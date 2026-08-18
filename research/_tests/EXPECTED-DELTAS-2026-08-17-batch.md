# EXPECTED entry-payload deltas for the 2026-08-17 batch (#183 #184 #185 + v3.0.2 DLL)
# Written BEFORE the rebuild. Any diff outside this list is a defect in the batch;
# any missing diff is a fix that failed to land.
#
# 1.5x ONLY (the #185 slab family — CellUnit height snap 60->54, art byte-exact
# at integer tiers per the refereed mechanism):
#   856ddbac 46a006b0 140155d2   60 -> 54 tall
#   856ddbac 46a006b0 140155d5   60 -> 54 tall
#   856ddbac 46a006b0 140155f2   60 -> 54 tall
#   856ddbac 46a006b0 140155f5   60 -> 54 tall
#   856ddbac 46a006b0 2bfeb0cc   60 -> 54 tall
#
# EVERY TIER (the align-attribute rewrites ride the builder's .UI transform,
# which runs per tier package):
#   00000000 96a006b0 2bc90671   two nodes: align lefttop -> leftcenter (#184)
#   00000000 08000600 2bc90671   same two nodes (twin)
#   00000000 96a006b0 aa920991   one node: align lefttop -> leftbottom (#183)
#   00000000 08000600 aa920991   same, ONLY if this twin is staged (absent = fine)
#
# NOT expected: any other art at any tier; the #182 fix is DLL-only (v3.0.2,
# 482,304-B-era lineage, version literal 3.0.2 — deployed in the same batch).
#
# OPEN QUESTION THIS DEPLOY ANSWERS (referee-flagged): #185's mechanism predicts
# the budget cutoff is INVISIBLE at 2x/3x, but the user reported the doc's
# issues "are in 2x and 3x". If budget cutoff persists at 2x after this batch,
# that is a SECOND mechanism, not a failed fix.
# #183 CONTINGENCY CORRECTED (review major-1): the sweep DOES scale the label
# (RGKID in capture 2026-08-17-082334: .UI 112x18 -> live 168x27), so
# leftbottom is LIVE, not a no-op — a wrong seat would be a visible new
# regression. If the figure still misbehaves after this batch, the remaining
# unmeasured quantity is textH-vs-box (a 1.5x font that fills the 27px box
# makes align inert); P2 is NOT the next step — it is already answered.

# --- appended 2026-08-17: #186 U-Drive-It mission bubble, art family PINNED
# --- at x3-of-design ("fixed 96") — REGRESSION.md #186
#
# 15x AND 2x SelectiveArt packages ONLY, 9 entries each (same 9 TGIs, same
# NEW bytes in both — the pinned art is generated once at factor 3 and is
# byte-identical to preview-3x):
#   856ddbac 46a006b0 094ac89a   48x48  (15x) /  64x64  (2x) ->  96x96
#   856ddbac 46a006b0 46a006a2   96x24        / 120x30       -> 180x45
#   856ddbac 46a006b0 62b99d31  116x24        / 152x32       -> 228x48
#   856ddbac 46a006b0 42e55fd4  192x44        / 256x58       -> 384x87
#   856ddbac 46a006b0 e78ffc90   96x36        / 128x48       -> 192x72
#   856ddbac 46a006b0 c2b66daa   48x48        /  64x64       ->  96x96
#   856ddbac 46a006b0 46a006a8   27x108       /  36x144      ->  54x216
#   856ddbac 46a006b0 46a006a5  225x26        / 300x34       -> 450x51
#   856ddbac 46a006b0 62b19ce9  144x152       / 192x200      -> 288x300
#
# ⚠ MEASURED CORRECTION to the task-side expectation "family changes in ALL
# THREE tier packages": the pinned art is byte-identical to preview-3x
# (verified per-file 2026-08-17), so the 3x package has ZERO #186 payload
# deltas — a 3x family delta IS a defect. Likewise the four .UI-routed
# members (144161ea, 82b99d9d, 46a006a7, e2b14588) and the excluded pair
# (46a006a4, 46a006a6) change in NO package at any tier — a delta on any of
# those six IS a defect. Entry COUNTS are unchanged in all three packages
# (same TGIs, new payloads).
#
# ⚠ COMPANION CHANGE THIS BATCH MUST CARRY: Test-DatIntegrity.ps1 #100
# bubble payload assertion (expects 32*factor) must be re-pointed to fixed
# 96 at every tier, or it goes red on a correct build at 15x/2x.

# --- #186 CORRECTED (review finding 1, 2026-08-17 evening): the pin covers
# ONE sheet, not nine - the other eight were engine class-default widget art
# (registered, not referenced; consumers tier-sized; pinning them would break
# message boxes / Load-Save / sliders at 1.5x and 2x).
# EXPECTED from the #186 rebuild: exactly ONE changed entry per affected tier:
#   856ddbac 46a006b0 094ac89a   48x48 -> 96x96 (15x) | 64x64 -> 96x96 (2x)
#   3x: ZERO delta (96x96 == preview-3x bytes already).
# Plus the v3.0.3 DLL (combo dy + COMBODY instrument) in the same deploy.
