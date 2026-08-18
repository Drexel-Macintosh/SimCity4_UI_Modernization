# EXPECTED entry-payload deltas for the 2026-08-16 batch rebuild (#172 #177 #173-adjacent)
# Written BEFORE the rebuild (thresholds-from-controls: the compare checks THIS list,
# any diff outside it is a defect in the batch, any missing diff is a fix that failed to land).
#
# INTEGER TIERS (2x AND 3x) - exactly 3 entries each, ALL from #172 (stock overhang is
# deliberately changed at integer tiers; everything else must be byte-identical):
#   856ddbac 46a006b0 14015547   (2x 296x42->288x42, 3x 444x63->432x63)
#   856ddbac 46a006b0 4b8da4a4   (2x 296x46->288x42, 3x 444x69->432x63)
#   00000000 08000600 c973b411   (.UI twin: Query 132->131)
#
# 1.5x - the #172 three (216x32 / 216x32 / twin), PLUS:
#   856ddbac 46a006b0 14015584   63x14 -> 66x14  (cell-first states=6; no-snap conflict resolved)
# PLUS the 21 #177 height-exact sheets:
#   1abe787d 6c29491f 68->66 | 46a006b0 0c3a2e71 42->41 | 46a006b0 13d14c60 33->32
#   46a006b0 13d14c70 33->32 | 46a006b0 13d14c80 33->32 | 46a006b0 13e14f80 60->54
#   46a006b0 13e14f91 60->54 | 46a006b0 13e14fa0 60->54 | 46a006b0 13e14fb0 60->54
#   46a006b0 13e14fb1 60->54 | 46a006b0 13e14fb2 60->54 | 46a006b0 13e14fb5 60->54
#   46a006b0 13e14fb6 60->54 | 46a006b0 13f1524a 33->32 | 46a006b0 14416301 96->90
#   46a006b0 14416302 96->90 | 46a006b0 14416303 96->90 | 46a006b0 1441631a 60->54
#   46a006b0 2bc1198a 87->86 | 46a006b0 ac101989 33->32 | 46a006b0 cbcb9a74 33->32
# (heights only; widths unchanged. Entries may appear in SelectiveArt-15x AND, where
# the same TGI ships there, DialogStatic-15x - attribute by TGI, not by package.)
#
# ALSO expected at 1.5x ONLY (review fix F7): ladder 46a006b0 14015549
#   re-encode ct=2 -> ct=6 + sRGB/gAMA/pHYs chunk splice. PIXELS IDENTICAL - any
#   pixel-level diff there is a defect, only the PNG container may change.
#   (The 1abe787d twin also re-encodes but exists ONLY in the preview tree -
#   no dat packages it, so it must NOT appear in any dat compare.)
# NOT expected anywhere else: 14015580 (still no-snap),
# any UncoveredIcons content change (new dats, not diffs). DialogStatic-15x remains
# 261 vs dist 262 (#178, decision owed - pre-existing).
#
# EXTENDED POST-MEASUREMENT (same evening): six more 1.5x entries, ALL the #177
# rule landing on DialogStatic-staged / clone-path sheets the selective-safe
# stage prediction could not see. Verified by IHDR decode old-vs-new, heights
# exactly R(h1x*1.5), widths untouched:
#   46a006b0 13f15254 78->77 (h1x=51) | 46a006b0 144161e0 32->30 (h1x=20)
#   46a006b0 470261e1 32->30 (clone of 144161e0) | 46a006b0 2c201cb0/b1/b2
#   60->54 (h1x=36 - the ledger's own worked example)
# ADJUDICATED REMOVALS (#178, decision still owed): DialogStatic 2x/3x drop
# {856ddbac,46a006b0,ea7f0eae} (CAM splash) making all tiers consistent at 261.
# Zero on-screen impact on this install (splash ships in gated CamUI).
