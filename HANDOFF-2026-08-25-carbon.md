# HANDOFF — 2026-08-25, Carbon Skin arc + #197 god dock

All background jobs were STOPPED mid-flight on request. This file is the
resume point. Everything below is committed and pushed (`23d4daa`).

## State of the machine

- Tier **1.5x**, everything armed, game closed. `SC4UIScale.ini`
  `ScaleFactor=1.5`, `AutoScale=0`.
- Scoty Carbon Skin 1.5 installed at `Plugins\zz-scoty-mods\` (12 dats + PDF).
  ⚠ The folder name is deliberately NOT the author's `z____scoty_mods` — see
  the comparator law in REGRESSION.md 2026-08-25.
- Eight `z_SC4UIScale_ZCarbon*` packages built + deployed, armed at `-15x`.
- Gates at last run: Test-DatIntegrity **ALL PASS** (50 dats, 56
  deployed==built), Test-ThirdPartyGates **ALL PASS** (14 gates),
  `carbon_final_census.py` **GREEN** (494/494, 0 drift, 23 intended
  takeovers), `verify_carbon_uninstall.py` **GREEN**.
- DLL is `4.3.0-dev`, built and deployed with the #197 cure.

## STATUS: #198 CLOSED - day/night AND terraform both CONFIRMED FIXED on
## screen by the user. The live-marker derivation is verified end to end.
## NEW open defect: scrolling the god DISASTER flyout breaks its buttons
## (investigation wf_77ea9591-219 running/parked).

## THE ONE THING TO DO FIRST (needs a launch)

Launch at 1.5x, enter a city, open **god mode**:

1. **Day/Night flyout** — does its ring now seat on its toolbar button?
   The log must contain one `UiSpike: MFIX 0xCA35CBED day/night marker live
   t=183 vs stock t=135 (x1.50 = 135) -> dock corrected by -48 px`.
2. **Terraform flyout** — open it. The log emits `MFIX-DIAG 0x49923239`.
   Report whether its ring seats on its button or sits high.
3. **Boxes jumping on first open after a city load** — the second reported
   defect, NOT yet diagnosed (its investigation was stopped). Note WHICH
   boxes, and whether it still happens now that the ZCarbon packages are
   armed (it may have been the pre-ZCarbon window — see below).

## #197 — what shipped, and the work left

**Shipped cure** (`src\UiSpike.cpp`, `[Flyout] GodMarkerFix`, default 1):
the god dock compares the LIVE `0x0000AAAA` marker against the measured
stock marker (scaled the same way) and corrects by the delta. Identity on a
stock install. Applies to `0xCA35CBED` day/night (stock marker t=90) and
terrain-fx (t=30, unchanged by carbon → delta 0).

**Measured facts** (both corpora, my own instrument + two independent
adjudicators):

| script | window | stock marker | carbon marker | consequence |
|---|---|---|---|---|
| `{96a006b0,aa356502}` day/night | 0xCA35CBED | (4,90,78,148) | (4,**122**,78,180) | dock 32*f too LOW → 48px @1.5x, 64 @2x, 96 @3x (**the reported defect**) |
| `{96a006b0,aaa44448}` terrain-fx | 0xCA35CBED | (4,30,54,70) | (4,30,54,70) | unchanged → correctly untouched |
| `{96a006b0,e9923283}` terraform | 0x49923239 | (4,90,78,148) | (4,**0**,78,58) | dock 90*f too HIGH → **135px @1.5x** — NOT yet corrected |

**⭐ THE RULE, derived and confirmed 3/3** (this is the real find — an
adjudicator reproduced it from raw bytes): the hand-tuned dock constants ARE
the alignment-marker rule precomputed on stock —

    offset = buttonLocalPos − markerLocalPos

- terraform:  (10,10)  − (4,90) = (6,−80)  == table row 1
- terrain-fx: (10,70)  − (4,30) = (6, 40)  == `kTerrfxOffY`
- day/night:  (10,250) − (4,90) = (6,160)  == `kDayNightOffY`

(buttons from the god toolbar script `{0,96A006B0,69E3D347}`, root
`(5,185,79,536)`, children l=10 t=10/70/130/190/250 at 74x58 — **byte
identical in stock and carbon**, so spawn geometry is not a confound.)

**⭐ THE DISAMBIGUATOR I DID NOT HAVE WHEN I HEDGED:** the marker element
carries `caption="0x49e95d2b"` — *it names the button it aligns to*. That
resolves the two-scripts-declare-0x49923239 ambiguity I cited as the reason
not to correct terraform. With the caption, the whole thing can be derived at
runtime and no stock-marker table is needed at all.

**NEXT STEP (recommended):** replace the stock-marker table with the general
rule — read the live marker, read its `caption` button id, look that button
up in the god toolbar, and compute `offset = buttonLocal − markerLocal` live.
That subsumes the shipped delta cure, fixes terraform (→ `(6,+10)`), and
works for any future mod. Verify it reproduces `(6,−80)/(6,40)/(6,160)`
exactly on stock before shipping — that triple IS the regression test.

⚠ One adjudicator verdict said "the CURE is materially incomplete and two
subsidiary claims are wrong" — I salvaged only its first ~2600 chars before
shutdown. **Re-read it in full on resume**:
`.claude\projects\...\subagents\workflows\wf_57d07b6d-ef5\journal.jsonl`
(the `refuted:false` records). Do that BEFORE extending the cure.

## Defect B — "boxes jump on first open after a city load" (UNDIAGNOSED)

The investigation was stopped mid-adjudication. Probe hypotheses worth
resuming (in `wf_57d07b6d-ef5/journal.jsonl`):
- The strongest lead: **no city session has ever run with the ZCarbon
  packages armed.** Between ~07:29 and ~08:43 today the skin was installed
  with NO carbon packages, so ~131 formerly-pre-scaled dialogs were born 1x
  and reactively scaled — which produces exactly "first open jumps". If the
  report came from that window, it may already be fixed. **Ask the user when
  they saw it.**
- A named set of NINE flyout roots has no pre-scale-while-hidden route (they
  do not exist at city load), so they can only ever be scaled reactively.
- The show-time gate (`IsVisible()`) means a window that spends city load
  hidden is still 1x at its first visible frame.
- Cheapest instrument: `[Probe] VisTrace` — but it is a guaranteed silent
  null at stock tier, so the tier must be ≥1.01 when it runs.

## Open items (lower priority)

1. `sc4pac` channel maintainer still needs notifying — package paths changed
   in v4.2.0 (external repo, not ours).
2. Carbon residuals, accepted: CAM startup splash `ea7f0eae` keeps our
   CAM-styled art (carbon's copy is UNSCALED-only); the WebText caption is
   carbon's by design.
3. `UPSTREAM-CARBON-REPORT.md` is written but not sent — it contains a real
   defect report for the skin author (carbon's CSI balloon reskins can never
   display: the drawer resolves the `0x1ABE787D` twin group and carbon ships
   none of them).
4. v4.3.0 is still `-dev`. No release cut.
