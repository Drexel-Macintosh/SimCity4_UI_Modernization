export const meta = {
  name: 'sc4-open-issue-triage',
  description: 'Adjudicate every open SC4UIScale issue: closable now, needs a launch, or genuinely open',
  phases: [
    { title: 'Adjudicate', detail: 'one agent per open issue, verify status against the code' },
    { title: 'Verify', detail: 'adversarially re-check every CLOSE verdict' },
    { title: 'Report', detail: 'ranked disposition' },
  ],
}

const ROOT = "<PROJECT-ROOT>"

const RULES = `
PROJECT ROOT: ${ROOT}

⛔ THIS UNIT IS READ-ONLY EXCEPT FOR .md STATUS LINES. You may update a status
line in _tests\\REGRESSION.md or a tracking doc. You may NOT edit code, builders,
.UI, .ini, .ps1, or anything under dist\\, _archive\\, _working-backup\\.
dist\\SC4TouchControls-* is FROZEN and must never be touched.

YOUR JOB is adjudication, not repair. For the issue you are given, decide which
ONE of these it is, and prove it:

  ALREADY-DONE   the work landed; cite the code/file:line that implements it and
                 the evidence it works. Say what status line should be written.
  CLOSABLE-NOW   a small, safe, doc-or-gate-only change would close it; describe
                 the exact change. DO NOT make it.
  NEEDS-LAUNCH   only an eyes-on run of the game can settle it; state the ONE
                 thing the user must look at, in one sentence.
  STILL-OPEN     real work remains; state the single next concrete step.
  NOT-A-BUG      the premise is false; prove it.

⚠ EVIDENCE RULES, learned the hard way on this project:
* A null is not evidence. If a probe/grep found nothing, prove it COULD have
  found the thing (state the positive control) before concluding absence.
* Never mark ALREADY-DONE from a comment, a doc, or a task title. Only from the
  code itself, or from a recorded user confirmation you can quote.
* An old note is more confidently wrong than a new one. Check dates.
* If the issue's premise references a mechanism, verify the mechanism still
  exists and still runs on that path.

RECENT CONTEXT (2026-08-16, verify rather than assume):
* #170 CLOSED user-confirmed - advisor row. Cause was build_selective_safe.py's
  double_subtree_areas scaling all four coords independently, giving an 82px
  window against an 83px art cell at 1.5x. Fixed with #148's leaf rule.
* KEY STRUCTURAL FACT: 0x6A15C767 is in kDataScaledSubtreeIds, so
  ScalePanelRoot RETURNS before the child loop - the runtime sweep never walks
  that subtree. Geometry has THREE producers: the runtime sweep, the static
  dialog builder, and the data pre-scale path.
* gate_btn_undercover.py was rewritten today and now passes with 0
  BUILDER-WRONG at every tier.
* PACKAGES.md corpus rebuild now routes through tools\\upscale\\Rebuild-Corpus.ps1.
* DBPF FILE hashes are not reproducible (header timestamp at offsets 25/29).
  Compare per-entry payload hashes.
* #162 (mayor's-hat + people hairlines) is OPEN and the user has explicitly
  DEFERRED it - do not propose work on it, just record it as deferred.
* #138 (intro video) is BACKLOG - do not raise it, do not work on it.
`

const DISPOSITION = {
  type: 'object',
  additionalProperties: false,
  required: ['issue', 'disposition', 'evidence', 'next_step', 'confidence'],
  properties: {
    issue: { type: 'string' },
    disposition: {
      type: 'string',
      enum: ['ALREADY-DONE', 'CLOSABLE-NOW', 'NEEDS-LAUNCH', 'STILL-OPEN', 'NOT-A-BUG'],
    },
    evidence: { type: 'string', description: 'file:line or quoted user confirmation' },
    next_step: { type: 'string', description: 'one concrete sentence' },
    status_line: { type: 'string', description: 'the status line to record, if any' },
    confidence: { type: 'string', enum: ['proved', 'likely', 'unverified'] },
  },
}

const VERDICT = {
  type: 'object',
  additionalProperties: false,
  required: ['stands', 'reason'],
  properties: {
    stands: { type: 'boolean' },
    reason: { type: 'string' },
    corrected_disposition: { type: 'string' },
  },
}

const ISSUES = [
  '#31 Stock-parity: geometry verified clean, pixel pass awaits unlocked screen. Is the pixel pass still needed, and is there an OFFLINE way to do it now that we have compositors in tools\\uimap\\emu?',
  '#70 Stock-resolution budget reference capture + parity pass. Marked in_progress. Determine what actually remains.',
  '#100 4x bubble art - DO NOT SHIP; flipping the flag alone predicts 8x at 2x tier. Is the hazard still live in the current code? Find the flag and the consumer.',
  '#104 WinMgr valid set is wholesale empty (1543 buckets, 0 entries) before the window tree tears down. Shutdown spin. Determine the real remaining step.',
  '#105 SPINPROBE built v2.57.0, armed via [UiSpike] SpinProbe=10, awaiting a capture run. Is the probe still present and correctly armed in the CURRENT source?',
  '#107 Outcome recorder built v2.58.0 to accumulate #104 spin rates from ordinary play. Still present? Any data collected?',
  '#112 Phase 0: clean user ini authored and gated; remaining work is folding it into the shipped package. Check _packaging and the shipped ini.',
  '#123 Re-verify the 1.5x disaster ring seat after v2.71.8 seat-scaling. Can this be settled offline with emu_subflyout.py?',
  '#124 Consolidate the DVMAP inline snap onto SnapMiniMapToBake. Is the duplication still there in UiSpike.cpp?',
  '#125 Config F - fill the Data Views map at 768 (renderer clamp + draw-time stretch). Still wanted, or superseded by #121s x8 terrain bake extension?',
  '#152 gate_namicons.py is RED on a pre-#149 assumption. Read the gate, find the stale assumption, and say exactly what to change.',
  '#160 Tiled backgrounds desynced from their windows at 1.5x. gate_tiled_seam.py currently reports 1.5x-only failures that are all sheet-LARGER-than-window (clipped). Is there any case where the sheet is SMALLER, which is the only one that can show a gap?',
  '#171 132 pre-scaled buttons ship an over-snapped ART cell at 1.5x (window right, sheet wrong - ScaleDim CellUnit takes LCM{3,4}=12 on an 84px sheet). Assess ONLY whether a builder-side fix is possible that does NOT change art dimensions game-wide.',
  '#145/#146/#147/#148 release readiness cluster: GitHub publish gate, third-party/Maxis derived content audit, Simtropolis bundle, near-vanilla verification. Assess as ONE unit: what is genuinely blocking, what is already satisfied.',
]

phase('Adjudicate')
const results = await pipeline(
  ISSUES,
  (iss) => agent(
    `${RULES}\n\nADJUDICATE THIS ISSUE:\n\n${iss}\n\n` +
    `Search the repo for its real current state. Read _tests\\REGRESSION.md for the ` +
    `history (grep it, it is 10k+ lines). Then give your disposition with proof.`,
    { label: `adj:${iss.slice(0, 22)}`, phase: 'Adjudicate', schema: DISPOSITION }
  ),
  (d, iss) => {
    if (!d) return null
    if (d.disposition !== 'ALREADY-DONE' && d.disposition !== 'NOT-A-BUG') return d
    return agent(
      `${RULES}\n\nADVERSARIAL CHECK on a CLOSE verdict. Someone wants to close this ` +
      `issue. Closing a live defect is the expensive error here - try hard to REFUTE ` +
      `them. Default to stands=false unless the evidence is airtight.\n\n` +
      `ISSUE: ${iss}\nVERDICT: ${d.disposition}\nEVIDENCE: ${d.evidence}\n` +
      `NEXT STEP: ${d.next_step}\n\nGo verify the cited evidence yourself.`,
      { label: `refute:${iss.slice(0, 18)}`, phase: 'Verify', schema: VERDICT }
    ).then(v => ({
      ...d,
      disposition: (v && v.stands) ? d.disposition : (v && v.corrected_disposition) || 'STILL-OPEN',
      refuted: !(v && v.stands),
      refute_reason: v && v.reason,
    }))
  }
)

const out = results.filter(Boolean)
const byDisp = {}
for (const r of out) byDisp[r.disposition] = (byDisp[r.disposition] || 0) + 1
log(`adjudicated ${out.length} issues: ${JSON.stringify(byDisp)}`)

phase('Report')
const summary = await agent(
  `${RULES}\n\nWrite the disposition report for the project owner. Order it so the ` +
  `ACTIONABLE things come first: what can be closed right now, what needs one game ` +
  `launch (and exactly what to look at), what is genuinely still open. Be blunt about ` +
  `anything where the evidence was weak. Do not pad. This person hates progress recaps ` +
  `- give them the CURRENT state and the next move, nothing else.\n\n` +
  JSON.stringify(out, null, 1).slice(0, 80000),
  { label: 'disposition-report', phase: 'Report' }
)

return { adjudicated: out.length, byDisposition: byDisp, issues: out, summary }
