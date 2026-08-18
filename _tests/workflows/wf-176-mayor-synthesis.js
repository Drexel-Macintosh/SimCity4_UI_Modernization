export const meta = {
  name: 'sc4-mayor-rating-15x-synthesis',
  description: 'Finish the paused #176 run: synthesise the 4 saved lanes and settle whether the HUD Mayor Rating bar is actually mis-rendered at 1.5x',
  phases: [
    { title: 'Render', detail: 'reconstruct the bar offline at 1x/1.5x/2x/3x from shipped art + the disassembled algorithm' },
    { title: 'Synthesize', detail: 'decision brief over the saved lane results + the render' },
  ],
}

const ROOT = '<PROJECT-ROOT>'
const SAVED = ROOT + '\\_tests\\workflows\\wf-176-mayor-rating-RESULTS.json'

const CONTEXT = `
PROJECT: ${ROOT} (SimCity 4 Deluxe 1.1.641 UI-scaling mod). READ-ONLY. Change nothing.

A four-lane investigation into the HUD Mayor Rating bar and the City Opinion Polls bars at
tier 1.5x already ran. ALL ITS RESULTS ARE SAVED VERBATIM AT:
    ${SAVED}
READ THAT FILE FIRST. Do not re-run those lanes.

WHAT IS ALREADY SETTLED - treat as established, do not re-derive:
 * The polls-panel background {46a006b0,2bbeb1af} shipped 780px wide at 1.5x against a 774px
   crop, losing its right border. FIXED and deployed 2026-08-16 17:09:53; it now ships 774x195.
   Integer tiers proven byte-identical by hash (2206/2206 at both 2x and 3x).
 * THE HUD MAYOR RATING CONTROLLER IS EXONERATED, by byte-exact disassembly of sub_7E8510:
   there is no separate indicator child; the controller GENERATES a bitmap at runtime and
   pushes it into window 0x8A517556 via cIGZWinBMP::SetBitmap ([iface vt+0x10]) at 0x7E8700.
   It does: v = clamp(rating+100, 0, 200); W = src->GetWidth[vt+0x24]; H = src->GetHeight[vt+0x28];
   buffer->Init(W,H); row = (H*v)/200 (__allmul/__alldiv) clamped to [0,H-1];
   srcRect = {0,row,W,row+1}; then a loop replicates that ONE ROW down the whole buffer,
   bounded by a re-read of the SOURCE height. Every dimension is read from the ART at runtime.
 * The art {46a006b0,14015549} is a 26-ROW VERTICAL FILMSTRIP, one row per rating state.
   Row 0 = 12 red ticks; red px/row descends 36,33,...,3; rows 12 AND 13 are byte-identical
   (the deadband); green ascends 3,...,36 to row 25. 26 states, 25 distinct images.
 * That art is an EXACT nearest-neighbour scale at every tier: 102x26 -> 153x39 / 204x52 /
   306x78, with 0 differing pixels against a pure floor(r/f) resample.
 * The live window was PROBED: DRAWPROBE win=0x8A517556 rect=(180,85 153x17) class=00ADF6A0,
   with the positive control line present. 153 = 102*1.5 exactly. Staged imagerect is
   (0,0,153,17) at 1.5x, (0,0,204,22) at 2x, (0,0,306,33) at 3x.
 * VERIFIED TODAY: the deployed z_SC4UIScale_SelectiveArt-15x.dat is the ONLY supplier of
   14015549 and ships it at 153x39. There is no competing dat and no stock fallback.

SIX DEAD ATTRIBUTIONS - DO NOT RE-PROPOSE ANY:
 1. the #175 Catmull-Rom smoothing;
 2. the CellUnit snap on the trend-bar art;
 3. cSC4WinAuraBar src-follows-dst tiling (WRONG WIDGET - that is the region bubble bar
    {46a006b0,14416327}, not the HUD bar);
 4. "imul 7 is the art's segment pitch" (measured pitch is 4px; those sites are the decline
    ARROW step);
 5. "the window or crop is wrong at 1.5x" (probe says proportional);
 6. "ragged tick pitch" - red ticks render 5px and green 4px because red origins are EVEN and
    green ODD under floor(x/f). REAL and 1.5x-only, but it is a sub-pixel texture difference,
    not a fill-length error.

THE STANDING PUZZLE: the user reports the Mayor Rating bar is wrong at 1.5x and correct at 2x
("Mayor rating is broken", "it's only half filled", "look at their formatting"), yet EVERY
quantity measured so far is exactly proportional. Either something outside the measured set is
wrong, or the bar renders identically at both tiers and the reported symptom belongs to an
adjacent element.

LAWS: MEASURE, DON'T INFER. NULL IS NOT EVIDENCE - state the positive control. The decisive
comparison is 1.5x vs 2x, never 1.5x vs 1x. Any explanation that would also break 2x or 3x is
WRONG, because those are user-confirmed good.
`

phase('Render')
const render = await agent(`${CONTEXT}

YOUR JOB: settle by RECONSTRUCTION whether the HUD Mayor Rating bar actually renders
differently at 1.5x than at 2x, for the SAME rating.

You have the exact algorithm (above) and the exact art. Write a throwaway python script that,
for a given rating value v in 0..200 and a given tier, reproduces what the player sees:
  1. load the shipped sheet for that tier from tools/upscale/preview-15x|preview|preview-3x
     (and tools/dbpf/extracted for 1x);
  2. H = sheet height, W = sheet width; row = (H*v)//200 clamped to [0, H-1];
  3. the drawn bar = sheet row 'row', replicated, then cropped to the staged imagerect
     (0,0,153,17) at 1.5x / (0,0,204,22) at 2x / (0,0,306,33) at 3x / (0,0,102,11) at 1x.

Then, for a SWEEP of ratings (do at least v = 0,25,50,75,100,110,125,150,175,200):
 A. Report, per tier, the FILL FRACTION of the resulting bar row - i.e. how far along the bar
    the coloured (red/green) content extends, as a fraction of bar width. Normalise so the
    tiers are directly comparable.
 B. ⭐ THE KEY QUESTION: does the 1.5x fill fraction MATCH the 2x fill fraction at the same
    rating? Tabulate 1x vs 1.5x vs 2x vs 3x side by side. Any rating where 1.5x disagrees with
    2x by more than one state is the defect. If they agree everywhere, SAY SO PLAINLY - that is
    an equally valuable answer and it means the bar is NOT the broken thing.
 C. Also report which SOURCE STATE each tier lands on (map the chosen output row back through
    floor(r/f)). The 1x state count is 26; verify 1.5x/2x/3x select the equivalent state.
 D. Note anything about the DEADBAND (source rows 12 and 13 are identical) that behaves
    differently at 1.5x - e.g. whether the deadband occupies a different number of rating
    values at 1.5x than at 2x, which would make the bar appear to "stick" near the middle.

Report actual numbers in a table. State your positive control (e.g. that your reconstruction
reproduces the known 1x appearance). Be explicit about MEASURED vs INFERRED.`,
  { label: 'render:bar-fill-sweep', phase: 'Render' })

phase('Synthesize')
const brief = await agent(`${CONTEXT}

Read the four saved lanes at ${SAVED} (13 entries: 4 lane results + 9 adversarial verdicts).

A reconstruction lane then rendered the bar offline across a rating sweep at every tier. Its
report:
---
${render}
---

Produce a decision brief in markdown, max 600 words:
 1. THE HUD MAYOR RATING BAR: is it actually mis-rendered at 1.5x? Answer from the
    reconstruction, not from vibes. If the tiers agree, say the bar is NOT the defect and name
    what the user is most likely actually seeing (candidates: the polls panel border just
    fixed; the label/text above it; the decline arrows; the 5px-vs-4px tick texture).
 2. THE POLLS BARS: what, if anything, is still wrong after the 2bbeb1af fix.
 3. THE SINGLE CHEAPEST NEXT MEASUREMENT that discriminates. Prefer offline. If it needs a
    launch, say exactly what to look at and at which tier.
 4. What remains genuinely UNKNOWN, stated as a gap.
Be blunt. Do not manufacture confidence. "The bar is fine and the symptom is elsewhere" is a
perfectly good conclusion if that is what the numbers say.`,
  { label: 'synthesize', phase: 'Synthesize' })

return { render, brief }
