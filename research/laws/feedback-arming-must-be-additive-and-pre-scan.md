# ⭐ ARMING MUST BE ADDITIVE AND PRE-SCAN

**A file that must not be armed must never enter the plugin scan, because
entering the scan IS the damage.** The win it takes is latched into the merged
index before any code of ours runs. Nothing we do afterwards un-takes it.

Established 2026-08-29 by shipping the opposite and watching it break.

---

## What was tried

Arming a tier by RENAMING files (`.dat` ↔ `.dat.x1-disabled`) is the one thing
that makes this mod impossible for a package manager to uninstall — sc4pac
removes files by manifest name, and 53 of 68 installed files sat under a
renamed name.

The replacement: let every tier load, then at `PostAppInit` close the DBPF
segment of the ones we do not want. A probe appeared to authorise it —
`SegmentCensus` found our dats as addressable children of the Plugins
multi-packed segment (272 children, 12 ours), and closing one made a key it
owned resolve to `SimCity 4 Deluxe\SimCity_1.dat`, the stock archive. That was
logged as **FALL-THROUGH WORKS**.

## What actually happened

At 3x, with the pass closing exactly the right files and refusing nothing, the
region view came back with garbled toolbar strips, FF00FF bleeding through the
region panel, and black bars.

The chain:

1. The exclusion switch was consulted at ONE site, `if (ExclusionModeOn())
   { active = true; }` inside `SyncDat` — and it was **unconditional**. It
   overrode the DEPENDENCY verdict as well as the tier verdict.
2. So ~30 files whose owning mod is ABSENT went live before the scan: eight
   `ZCarbon*` × 3 tiers, `NamIcons` × 3, `WebButtonUI` × 3.
3. They sort last (`z_SC4UIScale_ZCarbon…` in the override folder), so they
   **won** ~516 TGIs when the merged index was built. Measured:
   `ZCarbonUI-3x ∩ DialogStatic-3x` = 197 of 197 keys;
   `ZCarbonArt-3x ∩ SelectiveArt` = 280.
4. `Close()` vacated those wins **without promoting the runner-up**. The parent
   declares `RemovedResource(key, segment)`
   (`cIGZPersistDBSegmentMultiPackedFiles.h:45-46`) precisely because the
   key→child map has to be told; it was never called.
5. Resolution left the parent segment entirely. 499 keys fell to the stock
   archives and came back as **stock 1x art and stock 1x .UI scripts inside a
   3x runtime**; 17 existed nowhere and came back as nothing.

A 1x multi-state strip inside a scaled cell shows two states side by side and
indexes past the sheet; the uncovered remainder is the colour key; an imagerect
with no surface under it is black. Exactly the screen.

## Why the probe said yes

**It chose a key with exactly ONE live owner in the tree.** It therefore never
constructed the case that mattered — a key owned by a child being closed AND by
a sibling staying open. Its `FALL-THROUGH WORKS` verdict was the failure mode
misread as success: falling through to the stock archive is correct when
nothing of ours should own the key, and catastrophic when something of ours
still should.

⭐ **A probe that cannot construct the failing case cannot authorise the
design.** Before believing a probe, ask which case it would have had to see to
say no — and whether the input you handed it contained that case.

## The other defect this exposed, which is the deeper one

The exclusion pass and `SyncDat` were **two rule sets describing one outcome**,
and they drifted immediately:

* `-1x` is not in `kPackages` (it holds only `-4x`, `-3x`, `-2x`, `-15x`), so
  `z_SC4UIScale_SelectorUI-1x.dat` matched no tag, was classified
  "tier-independent, always stays", and sat live at 3x in the WINNING folder —
  shipping stock-geometry Graphic Options into a 3x UI.
* The same override nullified WebText's inverse gate.

⭐ **TWO MECHANISMS FOR ONE DECISION IS THE DEFECT, NOT THE BUG.** The wrong
screen was a symptom; the cause was that "which packages are legitimate" had
two implementations. Any replacement arming mechanism must be the ONLY
implementation, not a second one behind a switch.

## The consequence

Load-time exclusion is dead — and not conditionally on further measurement.
Even had sibling promotion worked, it is a post-hoc correction to an index that
is already latched, resting on engine behaviour we do not own, cannot
version-pin, and have one contradicted measurement of. In the best case it only
equals what the rename already achieves.

The whole mechanism was deleted rather than left behind a default-off ini key:
**a disproved mechanism behind a switch is a mechanism someone re-enables.**
`SegmentCensus` was KEPT — it is the instrument every future probe extends.

The replacement direction is content swap at a stable filename
(`SyncDatStable`, shipping for SelectiveArt since v4.0.3), armed in the
director constructor, which runs DURING the plugin scan. That satisfies the law
in the title: a gated-off package declares no contested TGIs, so the runner-up
is promoted by the engine's own scan-order logic at index-build time, in the
ordinary way — which is exactly what the rename buys by keeping the file off
disk, and exactly what `Close()` cannot produce.

Context: [[sc4pac-rename-blocker]] · [[sc4-subfolder-layout-v420]]
