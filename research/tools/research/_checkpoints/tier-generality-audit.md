# Tier-generality audit digest (2026-07-29 night; full report in agent transcript)

Verdict: 2x is solid; **1.5x and 3x are substantially broken today** — not by
rounding but by missing packages, exact-equality gates and integer knobs.
Model implementation to imitate everywhere: the U-Drive-It gauge hook
(gGaugeScale = f, dst = cw*m+0.5, clamped to live window).

## CLASS A — feature silently dead at 1.5x/3x
- A1 ItemIcons/ItemIconsSub exist ONLY as -2x (ScaleTier.cpp:326/333 syncs
  nothing at other tiers) → ALL ~266+130 menu icons revert 1x in scaled cells.
- A2 stage_icons.py has no --factor (hardcoded 2x preview dir) → can't build.
- A3 UiSpike.cpp:809 `selfW == 258` EXACT (129*2) → sub-flyout ring/bar/dock
  machinery never fires at 1.5x (194) or 3x (387). Fix: ScaleRound(129,f)±1.
- A4 :4446 disaster-container hook box (200..400 x 500..900) FAILS at 3x
  (423x1017) → whole disaster draw/click fix dead at 3x. Widen f-derived; the
  class check is the real identification.
- A5 gStripFieldScale int=2, NO ini key → cannot be 1.5; fix ScaleRound(sf4,f).
- A6 ClaimScale int used as divisor/modulus; atoi("1.5")=1 → claim stays 1x.
  Fix: latch claimOrig, write ScaleRound(claimOrig,f).
- A7 :1106 bar-tile gate `d[0]>=200&&<400` fails at 1.5x both containers.
  Fix buffer-relative: d[0] >= selfW-53-4.

## CLASS B — fires but misrenders
- B1 ring blit hardcoded *2 / >>1 (4 sites :999-1009,:1073-1083) → fractional
  NN like Upscale2x.cs:306.
- B2 gBarWiden int=2 → float via ScaleRound.
- B3 BarDX=-53 assumes widened=2x53; general: -(ScaleRound(53,f)-53).
- B4/B5 RingDX/DY are SCREEN px coupled to DockX/Y(design*f) — coupling only
  holds at f=2. Re-express ring nudges in design units. UNDETERMINED: needs a
  live 3x run (SubBltLog/RingCal), do NOT derive blind.
- B6 SubDockDX/DY screen-px (-53,-24); general form from half-sprite(40,26.5)
  and half-cell(23.5,18.5) scaled by f. 1.5x → (-45,...), 3x → (-69,...).
- B7 derive_subring.py has TWO hardcoded 2* and asserts (25,-6); add --factor.
  First-cut: f=1.5 → (≈-10,≈3), f=3 → (≈40,≈-24) — confirm live.
- B8 back-arrow claim rect `2*kSubArrow*` → ScaleRound.

## CLASS C
- C6/C7/C8 dead ×2 blocks (gFieldMask/gWinScale/gStrip2xSrc=0) — delete so a
  re-enable can't resurrect them. C1 rating arrow 7*f rounding cosmetic.
- C11 a stray SelectiveArt-4x.dat would enable a 4x tier with nothing else
  present (PackageInstalled tests SelectiveArt only) — same root as A1.

## CONFIRMED tier-safe (do not re-audit): kMayorFlyoutDock, kGodFlyoutDock,
kDVPins, MINIMAP/DVMAP/UDMAP (blitSize-driven), gauges hook, ScalePanelRoot/
ScaleSubtree, Classify, CodePatches (all 4), both .UI builders end-to-end,
MenuFix untagged-is-correct, FontStyle tier files carry stock-size clones.

## Fix order: A1+A2 → A3 → A5+A6 → A4+A7 → B1+B2 → B3 → B6+B7+B8 → B4+B5
(B4/B5 LAST and only with live 3x measurement). Then delete C6-C8.
