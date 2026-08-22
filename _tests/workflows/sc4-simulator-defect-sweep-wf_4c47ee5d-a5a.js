export const meta = {
  name: 'sc4-simulator-defect-sweep',
  description: 'Drive the offline simulator/gate suite at all tiers to find defects before the user does',
  phases: [
    { title: 'Run', detail: 'execute every gate + compositor across tiers' },
    { title: 'Hunt', detail: 'targeted hunts for known defect classes' },
    { title: 'Verify', detail: 'adversarially refute every finding' },
    { title: 'Report', detail: 'ranked, user-visible-first' },
  ],
}

const ROOT = "<PROJECT-ROOT> 1 Project\\1 Completed Projects\\SC4UIScale"
const EMU = `${ROOT}\\tools\\uimap\\emu`

const RULES = `
PROJECT ROOT: ${ROOT}
SIMULATOR / GATE SUITE: ${EMU}

⛔ READ-ONLY. Do not edit ANY file. Do not rebuild packages. Do not deploy.
You are hunting, not repairing. Report what you find with proof.

THE TIER NOW IN USE IS 3x (AutoScale on a 3840x2160 panel). 1.5x and 2x are
also shipped and must stay correct.

⛔ EVIDENCE LAWS - this project has paid for every one of these:
* A NULL IS NOT EVIDENCE. If a scan finds nothing, prove it COULD have seen the
  thing. State the positive control. "0 findings" without a control is a REFUSAL.
* AN INTEGER-TIER CONTROL IS MANDATORY for any fractional-tier metric. Run it at
  2x and 3x first; if it does not read exactly 0 there, the metric is measuring
  its own sampling pattern and must be discarded, not reported.
* A MODEL THAT WOULD CONDEMN STOCK IS BROKEN. Run any new check against 1x -
  anything it flags there is the instrument's fault.
* A GATE IS ONLY AS HONEST AS ITS SCOPE. State what each gate does NOT look at.
* GEOMETRY HAS THREE PRODUCERS on this project and a check that models one is
  blind to the other two:
    1. the runtime sweep      UiSpike::ScaleSubtree
    2. the static dialogs     build_dialog_static.py
    3. the DATA pre-scale     build_selective_safe.py::double_subtree_areas
  A subtree in kDataScaledSubtreeIds is NEVER walked by the sweep
  (ScalePanelRoot returns early, UiSpike.cpp ~14557). This exact blindness hid a
  user-visible defect for weeks (#170).
* DBPF file hashes are NOT reproducible (header timestamp, offsets 25/29).
  Compare per-entry payload hashes.

FRESH USER SIGHTINGS at 3x, unexplained - use as SEEDS, not as conclusions:
 (A) The "?" button 0x2988bc85 in the city dashboard (I-c973b411) looks cut off
     at the bottom and shows a reverse-L artefact. MEASURED ALREADY: its window
     equals its art cell EXACTLY at 1x/1.5x/2x/3x (64x50, 96x75, 128x100,
     192x150 against sheet 14415860 = 256x50 -> 768x150). So it is NOT a
     size mismatch. NOTE its design area is (26,-6,90,44) - the TOP IS NEGATIVE,
     so the window extends above its parent and is clipped. style=toggle.
     Find what actually explains a bottom cutoff and a reverse L.
 (B) The money (§1,319) and population (158,768) readouts in the same dashboard
     sit HIGH in their rounded boxes - and the user reports this is true at
     1.5x, 2x AND 3x. Tier-independent means it is NOT a rounding bug. Suspects:
     our generated FontStyle.ini metrics vs the box, a text vertical-anchor
     constant, or it is stock behaviour. Determine which, and say how to prove
     it without a launch if possible.
`

const FINDING = {
  type: 'object',
  additionalProperties: false,
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['title', 'where', 'tiers', 'evidence', 'user_visible', 'why_it_draws'],
        properties: {
          title: { type: 'string' },
          where: { type: 'string', description: 'script id / window id / file:line' },
          tiers: { type: 'string', description: 'which tiers, and the integer-tier control result' },
          evidence: { type: 'string', description: 'the numbers, and the command that produced them' },
          user_visible: { type: 'string', enum: ['would-draw', 'probably-invisible', 'unknown'] },
          why_it_draws: { type: 'string', description: 'the mechanism from number to pixel' },
          producer: { type: 'string', description: 'which of the three geometry producers owns it' },
        },
      },
    },
    scope_not_covered: { type: 'string', description: 'what this pass could NOT see' },
  },
}

const VERDICT = {
  type: 'object',
  additionalProperties: false,
  required: ['is_real', 'reason'],
  properties: {
    is_real: { type: 'boolean' },
    reason: { type: 'string' },
    severity: { type: 'string', enum: ['ship-blocker', 'visible', 'cosmetic', 'noise'] },
  },
}

const LANES = [
  { k: 'gates-all-tiers', p: `Run EVERY gate_*.py in ${EMU} at --tier 15x, 2x and 3x where the gate supports tiers. Collect exit codes and headline numbers. Report every gate that FAILS, every gate that reports a nonzero "known residual" it has chosen not to fail on, and every gate that SKIPS. A nonzero residual that vanishes at the integer tiers is a DEFECT, not a residual (that rule found #170). Also flag any gate that cannot run at all - a broken instrument is a finding.` },
  { k: 'prescaled-audit', p: `The DATA pre-scale path is the newest and least-audited geometry producer. Enumerate EVERY subtree that build_selective_safe.py pre-scales (grep double_subtree_areas and double_one_window_area call sites), and for each, check every child window against the art it binds, at all three tiers, VERBATIM (the shipped number is final - the DLL never walks these). #170 fixed the state-strip buttons; check the OTHER node classes in those same subtrees - GZWinBMP with imagerect, GZWinText, containers, 9-slice frames.` },
  { k: 'compositor-3x', p: `Use the offline COMPOSITORS - render_flyout.py and render_dialog.py in ${EMU} - to actually LOOK at panels at 3x and compare against 1x and 2x. Read their docstrings first for usage and for what they do NOT model. Prioritise the city dashboard I-c973b411, the advisors I-4a160034/I-cbc905cd, and any flyout. Report anything visibly wrong. This suite's own README says the rest of it "NEVER LOOKS AT A PIXEL" - you are the half that does.` },
  { k: 'seed-questionmark', p: `SEED (A): the "?" button 0x2988bc85. Its window equals its art cell at every tier, so stop looking at size. Investigate: what clips it? What is its PARENT and does the parent's rect cover it (its top is -6, i.e. above the parent origin)? Does style=toggle change the state count or the cell divide? Is 14415860 a 4-state strip at all, or 2-state (a toggle) - if it is 2-state, cell = 128x50 at 1x and EVERYTHING computed on /4 is wrong. Check tools\\upscale\\cell-strips.txt for its declared state count and check find_cell_strips.py for how that count was derived.` },
  { k: 'seed-textbaseline', p: `SEED (B): money and population readouts sitting HIGH at every tier. Find those windows in I-c973b411, identify their class and their font= style, then compare our generated FontStyle tier files against FontStyle.default.ini for those styles - not just the size field, but every field that affects vertical placement. Determine whether the high seat is (a) ours, (b) stock, or (c) undecidable offline. If undecidable, state the ONE stock-compare step that settles it.` },
  { k: 'negative-origin', p: `The "?" button has a NEGATIVE design top (-6). Law 89 says a negative origin used to round outward and lengthen a span; that was fixed by RoundHalfUp. CENSUS every window in the whole staged corpus with a negative l or t, at every tier, and check each one's scaled geometry for a span that changed length versus its 1x design. Integer-tier control mandatory.` },
  { k: 'font-metrics', p: `Audit the font pipeline end to end: tools\\fonts\\make_fontstyle.py, its --selfcheck, and the three shipped FontStyle-*.ini. Verify each tier file is exactly what the generator produces TODAY (regenerate to a temp path and diff - do not overwrite the shipped files). Report any style present in one tier and absent in another, any size that is not round(base*factor), and any field other than size that differs between tiers when it should not.` },
  { k: 'threex-regression', p: `3x was user-confirmed clean on 2026-08-14. Determine EXACTLY what has changed in the 3x shipping packages since then, by comparing per-ENTRY payload hashes (never file hashes). For every entry that changed, name the change that caused it and whether it was proven a no-op. This is the bisection boundary for any new 3x defect.` },
  { k: 'crosscheck', p: `Run tools\\uimap\\diff and any crosscheck.py / Test-*.py harness that runs offline, at all tiers. Report failures and, importantly, every SKIP or DEFERRAL - crosscheck.py is documented as exiting 0 with 9 named SKIPS and 8 guarded DEFERRALS, which means its exit code is not coverage. State what is genuinely unverified.` },
  { k: 'thirdparty', p: `Audit the third-party gated overrides (ScaleTier::kThirdPartyDeps, ThirdPartyUI, CamUI, WarriorUI, NamIcons). For each: is the gate live, does the override still match the mod version installed, and would removing the mod leave our copy stranded? Also check the 1abe787d shadow art group - it holds copies of the advisor sheets byte-identical to 46a006b0 at 1x but built WITHOUT --cell-strips. Prove whether it reaches any shipped package.` },
]

phase('Run')
const swept = await pipeline(
  LANES,
  l => agent(`${RULES}\n\nLANE: ${l.k}\n\n${l.p}\n\nRun things. Report numbers, not impressions.`,
             { label: `sweep:${l.k}`, phase: 'Run', schema: FINDING }),
  (res, l) => {
    const fs = (res && res.findings) ? res.findings : []
    if (!fs.length) return { lane: l.k, confirmed: [], scope: res && res.scope_not_covered }
    return parallel(fs.map(f => () =>
      parallel([
        () => agent(`${RULES}\n\nREFUTE THIS FINDING - correctness lens. Is the arithmetic right? Is the integer-tier control actually clean? Default is_real=false if you cannot reproduce it.\n\n${JSON.stringify(f)}`,
                    { label: `refute-math:${f.title.slice(0,18)}`, phase: 'Verify', schema: VERDICT }),
        () => agent(`${RULES}\n\nREFUTE THIS FINDING - does-it-draw lens. Even if the numbers are right, would a player SEE it? Trace number to pixel: what blits, is it clipped or stretched, is the window even visible. Many true numbers on this project are invisible (law 61: GZWinBtn cell/window mismatch is normal). Default is_real=false.\n\n${JSON.stringify(f)}`,
                    { label: `refute-draw:${f.title.slice(0,18)}`, phase: 'Verify', schema: VERDICT }),
      ]).then(vs => {
        const ok = vs.filter(Boolean)
        const real = ok.filter(v => v.is_real).length
        return { ...f, survived: real >= 1 && ok.length > 0, votes: ok }
      })
    )).then(vs => ({ lane: l.k, confirmed: vs.filter(x => x.survived), scope: res.scope_not_covered }))
  }
)

const lanes = swept.filter(Boolean)
const total = lanes.reduce((n, l) => n + l.confirmed.length, 0)
log(`${total} findings survived adversarial verification across ${lanes.length} lanes`)

phase('Report')
const report = await agent(
  `${RULES}\n\nWrite the sweep report. Rank STRICTLY by "would a player see this", ` +
  `ship-blockers first. For each: what it is, where, which tiers, the mechanism from ` +
  `number to pixel, and the ONE next step. Then a section listing what this whole ` +
  `sweep could NOT see - be honest, the scope nulls are as valuable as the findings. ` +
  `Finally, adjudicate the two user seeds (A) the "?" button and (B) the high text ` +
  `baseline - say plainly whether the sweep explained them or not.\n\n` +
  `LANES:\n${JSON.stringify(lanes, null, 1).slice(0, 90000)}`,
  { label: 'sweep-report', phase: 'Report' }
)

return { lanes: lanes.length, findings: total, report }
