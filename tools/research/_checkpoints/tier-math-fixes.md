# Tier-math fix pass (v2.24.0-tiermath) — COMPLETE 2026-07-29 night

FINAL: built (MSBuild Release/Win32, clean), deployed (game absent: SC4UIScale.dll
v2.24.0-tiermath live + 4 tier dats gated .x1-disabled beside the live -2x ones),
suites green (DatIntegrity "ALL PASS (15 dats + 3 font sources + 2 DLLs +
frozen-bundle hash)"; ScaleTierDecide "ALL PASS (14 named cases + 5000x2 random
fit sweep)"; derive_subring f=2 "ALL PASS"). REGRESSION.md "TIER MATH PASS
(v2.24.0)" section appended with the full substitution table + trap signature
(any 2x visual change after v2.24.0 = a formula that did not reduce to its old
constant). B4/B5 untouched per exclusion. AWAITING EYES-ON at 2x (expected: zero
visual change); 1.5x/3x flyout machinery now fires but SubRingDX/DY at those
tiers remain PROVISIONAL (confirm live) and B4/B5 need a live 3x measurement.

Spec: tier-generality-audit.md (same folder). Directive: every constant becomes its
derived form; f=2 must reproduce the old behaviour EXACTLY (2x is the regression baseline).

## Status log
- 2026-07-29: BARRIER cleared on first read — SC4UIScaleDllDirector.cpp already at
  "2.23.3-lifecycle" (the lifecycle agent finished before this pass started). Safe to edit src\.
- Step 0 (survey) DONE. Key facts established:
  * ScaleTier.cpp lines 324-341 ALREADY loop SyncDat over all four kPackages tags for
    z_SC4UIScale_ItemIcons AND zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub — the sync list is
    already general; SyncDat early-returns when no file exists. A1's real gap = the packages.
  * preview-15x/SimCity_1 and preview-3x/SimCity_1 exist (2206 files each, all 356
    G-0x6a386d26 icons present) — no upscaler run needed for the ROOT ItemIcons tiers.
  * Sub composition (pack-sub, 130) = submenus-1x(55) + plugins-1x(69) + lots-icons-1x(5)
    all upscaled + missing-thumb 0x144161EC taken from the stock preview set. Verified by
    set-difference against the shipped pack-sub.
  * Deployed live-tune ini (Documents\SimCity 4\Plugins\SC4UIScale.ini) carries 2x-tuned
    SubDockDX/DY=-53/-24 ([Flyout]) and BarDX=-53/BarW=2 ([Disaster]) which would override
    any in-code general form. Plan: derive in code, comment those 4 values out (f=2 derived
    values == the old ini values EXACTLY, proven below). RingDX/RingDY/DockX/DockY (B4/B5)
    untouched per exclusion. SubRingDX/DY=25/-6 stay (B7 is tool-side only; 2x is live tier).
  * `settings.spikeScaleFactor` is not visible to the namespace-scope draw hooks; adding
    float gTierF (default 2.0f) set at ScaleGodFlyouts/ScaleMenuFlyouts entry. Hooks only
    install from those sweeps, so gTierF is always current before any hook fires.
  * ScaleRound (llround) lives at line ~2632, BELOW the hooks — moving it up top; adding
    RoundHalfUp (floor(v+0.5)) matching the art pipeline (Upscale2x/scale_len) for the new
    forms (differs from llround only at negative half values, e.g. -16.5*3).

## f=2 identity table (RHU = RoundHalfUp = floor(v+0.5), the art-pipeline rule)
| Item | Old constant/expr (2x live behaviour) | General form | f=2 value | Match |
|------|---------------------------------------|--------------|-----------|-------|
| A3 sub gate | `selfW == 258` | `|selfW - RHU(129f)| <= (f integer ? 0 : 1)` | RHU(258)=258, tol=0 → ==258 | EXACT |
| A3/A4 disaster gate | `selfH>500 && 200<selfW<400` | `selfH>RHU(250f) && RHU(100f)<selfW<RHU(200f)` | 500/200/400 | EXACT |
| A4 hook box | `w in [200,400], h in [500,900]` | `[RHU(100f),RHU(200f)] x [RHU(250f),RHU(450f)]` | 200/400/500/900 | EXACT |
| A5 strip fields | `sf * 2` (gStripFieldScale) | `RHU(sf * f)` (flag = enable only) | sf*2 | EXACT |
| A6 claim write | `oldW * 2` | `gClaimOrig=oldW; RHU(oldW*f)` | oldW*2 | EXACT |
| A6 claim restore | `v in[60,120] && v%2==0 -> v/2` | `v == RHU(gClaimOrig*f) -> gClaimOrig` | v==2*orig -> orig | EXACT on all occurring inputs (field only ever holds 1x or our write; old form would also have halved a hypothetical never-occurring even value we didn't write) |
| A7 bar-tile gate | `d[0] in [200,400)` | `d[0] in [selfW-57, selfW)` | sub [201,258), disaster [225,282) | EXACT on all occurring inputs (game blits every bar tile at exactly selfW-53: SBLT 205=258-53, cap 229=282-53; positions the forms disagree on carry no blits or are fully off-buffer no-ops) |
| B1 ring loops (4 sites) | `sh*2 / oy>>1, sw*2 / ox>>1` | `RHU(s*f) / floor(o/f)` | 2s / o>>1 | EXACT (bit-identical pixels) |
| B2 bar widen | `int gBarWiden=2` (ini BarW=2) | `float, auto = f; dst=RHU(sw*W), src=floor(ox/W)` | W=2 → sw*2, ox/2 | EXACT |
| B3 bar shift | ini `BarDX=-53` (compiled -45 was dead - ini always loaded) | `53 - RHU(53*W)` auto | 53-106 = -53 | EXACT vs live 2x |
| B6 sub dock | ini `SubDockDX/DY=-53/-24` | `RHU(-16.5f)-20, 29-RHU(26.5f)` auto | -33-20=-53, 29-53=-24 | EXACT vs live 2x |
| B7 tool | hard assert (25,-6) | per-tier table; f=2 exact-asserted; chain `f*e - (n + dock(f) + r(f) + f*h)` | (25,-6) | EXACT (script run: ALL PASS) |
| B8 arrow rect | `2*48-4, 2*10-4, 2*66+4, 2*44+4` | `RHU(k*f) +- 4` (slop unscaled, preserved) | 92/16/136/92 | EXACT |
| C6/C7/C8 | gFieldMask/gWinScale/gStrip2xSrc (all 0, dead) | DELETED | no code path | EXACT (never executed at 2x) |

Derived non-2 values for the record: SubDock 1.5x=(-45,-11), 3x=(-69,-51) (digest's
first-cut -45/-69 DX reproduced); BarDX 1.5x=-27(W=1.5), 3x=-106(W=3); sub gate
1.5x=193..195, 3x=387; hook box 3x=300..600 x 750..1350 (contains 423x1017).
B7 derived: 1.5x=(19,-4) 3x=(37,-8), PROVISIONAL (digest first-cut differed:
~(-10,3)/~(40,-24)) - confirm live via SubBltLog/RingCal before shipping tier inis;
ini SubRingDX/DY stay at the 2x-confirmed 25/-6 (2x is the live tier).

## Items
- [x] A1+A2 DONE (build side): stage_icons.py --factor (build_selective_safe conventions:
      tag derivation, preview-<tag> input, tagged collision guards refmap-<tag>/packages
      dats, pack to tools\packages\<tag>\z_SC4UIScale_ItemIcons-<tag>.dat; --factor 2 =
      legacy stage-only, bit-identical). NEW tools\itemicons\build_itemicons_sub.py
      replicates the pack-sub path per tier (129 1x sources upscaled + missing-thumb
      0x144161EC from the tier preview set; name-set verified == shipped 2x pack-sub).
      BUILT: ItemIcons-15x (266, 264x66 strips), ItemIcons-3x (266, 528x132),
      ItemIconsSub-15x (130), ItemIconsSub-3x (130). 2x verify-run: set identical, shipped
      dat untouched. ScaleTier.cpp: NO change needed - lines 324-341 already sync both
      bases for all 4 tags (documented). Test-DatIntegrity.ps1: 4 entries added w/ dated
      comment. Deploy (gated .x1-disabled) happens in the final deploy step.
- [x] A3 selfW==258 exact gate -> RHU(129f) w/ integer-factor zero tolerance (+ the
      disaster destIsContainer band derived too - required by A4's intent, same block)
- [x] A5 gStripFieldScale -> RHU(sf*f), flag = enable switch
- [x] A6 ClaimScale -> enable flag + gClaimOrig latch + RHU(orig*f) write / exact restore
- [x] A4 disaster hook box -> RHU-derived design band 100..200 x 250..450
- [x] A7 bar-tile gate -> buffer-relative d[0] >= selfW-53-4 && < selfW
- [x] B1 ring blits (disaster + sub, 4 sites) -> fractional NN (RHU dims, floor(o/f) sample)
- [x] B2 gBarWiden -> float, auto = tier factor, ini BarW atof
- [x] B3 gBarDX -> auto 53-RHU(53*W); deployed ini BarDX/BarW commented out (were 2x pins)
- [x] B6 gSubDockDX/DY -> auto derived; deployed ini values commented out (were 2x pins)
- [x] B7 derive_subring.py --factor + per-tier expectation table (f=2 exact-assert PASSES)
- [x] C6/C7/C8 gFieldMask/gWinScale/gStrip2xSrc deleted (decls + bodies + gate refs)
- [x] Version -> 2.24.0-tiermath; MSBuild Release/Win32 CLEAN
- [x] B4/B5 EXCLUDED per spec (UNDETERMINED, needs live 3x measurement) — untouched
