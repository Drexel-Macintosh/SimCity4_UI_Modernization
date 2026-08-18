---
name: reference-sc4-exception-reports
description: "SimCity 4 writes its own crash reports to Documents\\SimCity 4\\Exception Reports\\ with the faulting EIP, registers and module list - read them FIRST on any crash, before reasoning about bytes. Windows WER is useless on this machine (zero app reports ever)."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-04T20:33:08.978Z
---

**The game writes its own crash artefact. Read it before anything else.**

`C:\Users\<user>\OneDrive\Documents\SimCity 4\Exception Reports\`
→ `SimCity Exception Report YYYY.MM.DD HH.MM.SS.txt`

Each one carries: exception code, **`CS:EIP` = the faulting instruction**, the full
register set, `Section:Offset`, the exe version (1.1.641.0), and the loaded-module
list with base addresses. That is a **measurement** of where the game died, free,
already on disk, no build and no user test required.

⚠ **Windows WER is a structural null here.** No `Application Error` event and no
`.wer`/`.dmp` is produced for this game — the machine has produced **zero** WER app
reports ever, so "no WER record" proves nothing. The game's own handler catches the
fault, writes its report, and exits. Do not read WER silence as evidence.

## How it closed #109 (2026-08-04)

Twelve reports existed. **Five fault at the identical instruction `0x00910010`** —
`ACCESS_VIOLATION`, the `rep stosd` inside the game's row fill — at tier 1.5× and
tier 3× alike, and **never at 2×**. One tier crashes, one does not, same
instruction ⇒ a geometry invariant, and a measurable one.

It also **refuted** the cause this project had written into every doc for two
weeks (a non-power-of-two `blitSize` overrunning the raster). See
[[reference-sc4-minimap-bake]] for the corrected invariant: the **WINDOW** and the
**SURFACE** disagree at fractional tiers, not `blitSize` and `terrainDim`.

## The rule

**On any crash: `ls` that directory first.** Match report timestamps to the tail of
`SC4UIScale.log` (the logger `fflush`es per line, so the log tail survives). If two
reports at different tiers share an EIP, you have the discriminator before you have
written a line of analysis.

Cost of not doing this: ~50 minutes of the user's time on a five-agent workflow,
reasoning about bytes, while the answer sat in a text file. See
[[feedback-sc4-measure-dont-infer]] — a faulting EIP is a MEASUREMENT.
