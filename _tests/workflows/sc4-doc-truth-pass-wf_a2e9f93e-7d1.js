export const meta = {
  name: 'sc4-doc-truth-pass',
  description: 'Audit SC4UIScale documentation against the current code and correct every stale or false claim',
  phases: [
    { title: 'Audit', detail: 'one agent per doc cluster, verify claims against code' },
    { title: 'Verify', detail: 'adversarially re-check each finding against the code' },
    { title: 'Apply', detail: 'apply only CONFIRMED corrections, markdown only' },
    { title: 'Report', detail: 'synthesise' },
  ],
}

const ROOT = "<PROJECT-ROOT>"

const RULES = `
PROJECT ROOT: ${ROOT}

⛔ HARD CONSTRAINTS - violating any of these is a failed unit:
* You may ONLY edit .md files. NEVER edit .py, .cs, .cpp, .h, .ps1, .ui, .ini, .dat, .png.
* NEVER touch anything under dist\\, _archive\\, _working-backup\\, vendor\\, or
  tools\\dialog-static\\REPORT*.md (generated build reports - not hand-maintained).
* NEVER delete a document. Correct claims in place; strike through a wrong claim
  with ~~...~~ and write the correction beneath it with the date 2026-08-16 and
  the evidence (file:line), matching the house style already in these files.
* DO NOT "tidy", reformat, reflow, or restructure. Only change statements that
  are FALSE or STALE about the current code.
* A claim is only stale if you VERIFIED it against the current source. Quote the
  file:line you checked. If you cannot verify it, leave it alone and report it as
  UNVERIFIED - do not guess.

CONTEXT YOU MUST KNOW (all landed 2026-08-16, verify rather than assume):
* #170 CLOSED, user-confirmed: the seven advisor buttons x2 scripts
  (I-4a160034, I-cbc905cd) shipped an 82px window against an 83px art cell at
  1.5x. Cause: build_selective_safe.py::double_subtree_areas scaled all four
  coordinates independently. Fix: #148's leaf rule (no children + image= + no
  imagerect -> size-derived) now applied there too.
* Crucially: 0x6A15C767 is in kDataScaledSubtreeIds, so ScalePanelRoot RETURNS
  before the child loop (UiSpike.cpp ~14557). The runtime sweep NEVER walks
  those buttons. Any doc claiming ScaleSubtree or #167's stripBtnClass governs
  the advisor row is WRONG.
* #169's per-state art sampling is correct but does not change the resting
  state (output col 82 samples src col 54 under both samplers).
* gate_btn_undercover.py was rewritten: it now pairs staged nodes with their 1x
  design by document order, judges pre-scaled nodes verbatim, and splits its
  verdict by cause (BUILDER-WRONG vs art snapped by ScaleDim).
* PACKAGES.md step 1 now points at tools\\upscale\\Rebuild-Corpus.ps1. Any doc
  that still shows a bare Upscale2x.exe corpus command WITHOUT --cell-strips,
  --nine-slice and --no-snap is documenting a command that silently un-ships
  three user-confirmed fixes.
* DBPF file hashes are NOT reproducible: 2 bytes at offsets 25 and 29 are a
  header timestamp. Any doc telling a reader to compare dat FILE hashes to prove
  a no-op is wrong - the correct comparison is per-entry payload hashes.
* #171 is newly split out: 132 pre-scaled buttons at 1.5x whose ART cell is
  over-snapped by ScaleDim's CellUnit (window right, sheet wrong). 0 at 2x/3x.
* Still open and NOT fixed: #162, the mayor's-hat and people-button hairlines in
  I-c973b411. Geometry is exact, art is a faithful NN copy, not a tiled seam.
  Do not write that it is fixed.
`

const FINDINGS = {
  type: 'object',
  additionalProperties: false,
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['doc', 'line', 'claim', 'why_wrong', 'evidence', 'correction', 'severity'],
        properties: {
          doc: { type: 'string' },
          line: { type: 'number' },
          claim: { type: 'string', description: 'the stale/false text, quoted' },
          why_wrong: { type: 'string' },
          evidence: { type: 'string', description: 'file:line in the CODE that proves it' },
          correction: { type: 'string', description: 'exact replacement markdown' },
          severity: { type: 'string', enum: ['misleads-a-fix', 'wrong-fact', 'cosmetic'] },
        },
      },
    },
  },
}

const VERDICT = {
  type: 'object',
  additionalProperties: false,
  required: ['is_real', 'reason'],
  properties: {
    is_real: { type: 'boolean' },
    reason: { type: 'string' },
    corrected_correction: { type: 'string' },
  },
}

const CLUSTERS = [
  { key: 'regression', docs: '_tests\\REGRESSION.md — focus ONLY on the last 1500 lines (entries #154 onward) plus any entry that states a conclusion about the advisor row, ScaleSubtree, kDataScaledSubtreeIds, cell-vs-window, or dat hash comparison. This file is 10k+ lines; do not read it all, grep it.' },
  { key: 'engine', docs: 'tools\\research\\SC4-UI-ENGINE.md — the widget catalogue and any section on GZWinBtn cell math, blit behaviour, or which windows the sweep reaches.' },
  { key: 'triage', docs: '_tests\\TRIAGE-PLAYBOOK.md and tools\\research\\TRIAGE.md — the symptom->family routing, especially anything routing a 1.5x cell/window symptom.' },
  { key: 'packages', docs: 'tools\\packages\\PACKAGES.md, README.md, START-HERE.md — build/deploy commands and package inventory. Verify every command line actually exists and every flag is real (check tools\\upscale\\Upscale2x.cs argument parsing).' },
  { key: 'hardening', docs: '_tests\\HARDENING-PROPOSALS.md and _tests\\PROBES-NEEDED.md — mark any proposal that is now IMPLEMENTED or now MOOT, with evidence.' },
  { key: 'emu', docs: 'tools\\uimap\\emu\\README.md and the docstrings quoted inside it — the suite scope claims. gate_btn_undercover.py changed materially today.' },
  { key: 'mechanisms', docs: 'tools\\research\\MECHANISM-GENERATIONS.md, tools\\research\\SCALING-AXES.md, tools\\selective-safe\\SELECTIVE-SAFE.md (if present) — which families are on which generation, and the geometry-producer story.' },
  { key: 'scenarios', docs: '_tests\\SCENARIOS.md, tools\\uimap\\coverage-matrix.md, tools\\uimap\\BUILDER-CENSUS.md — coverage and scenario claims.' },
]

phase('Audit')
const audited = await pipeline(
  CLUSTERS,
  c => agent(
    `${RULES}\n\nYou are auditing this documentation cluster for FALSE or STALE claims:\n\n${c.docs}\n\n` +
    `Read the doc(s), then VERIFY each substantive claim against the current source. ` +
    `Report only claims you proved wrong, with the code file:line that proves it. ` +
    `Prioritise claims that would MISLEAD SOMEONE FIXING A BUG - a wrong premise in ` +
    `these files has killed correct candidates repeatedly. Do NOT edit anything yet.`,
    { label: `audit:${c.key}`, phase: 'Audit', schema: FINDINGS }
  ),
  (res, c) => {
    const fs = (res && res.findings) ? res.findings : []
    if (!fs.length) return { key: c.key, confirmed: [] }
    return parallel(fs.map(f => () =>
      agent(
        `${RULES}\n\nADVERSARIAL CHECK. Someone claims this documentation line is WRONG. ` +
        `Try to REFUTE them. Default to is_real=false if you cannot independently prove the doc is wrong.\n\n` +
        `DOC: ${f.doc} line ${f.line}\nCLAIM IN DOC: ${f.claim}\n` +
        `AUDITOR SAYS: ${f.why_wrong}\nAUDITOR'S EVIDENCE: ${f.evidence}\n` +
        `PROPOSED CORRECTION: ${f.correction}\n\n` +
        `Go read the cited code yourself. Is the doc actually wrong? Is the proposed ` +
        `correction actually right? If the correction is itself inaccurate, supply a fixed one.`,
        { label: `verify:${f.doc.split('\\\\').pop()}:${f.line}`, phase: 'Verify', schema: VERDICT }
      ).then(v => ({ ...f, verdict: v }))
    )).then(vs => ({
      key: c.key,
      confirmed: vs.filter(Boolean).filter(x => x.verdict && x.verdict.is_real)
        .map(x => ({ ...x, correction: x.verdict.corrected_correction || x.correction })),
    }))
  }
)

const all = audited.filter(Boolean)
const total = all.reduce((n, a) => n + a.confirmed.length, 0)
log(`confirmed ${total} stale/false documentation claims across ${all.length} clusters`)

phase('Apply')
const applied = await parallel(all.filter(a => a.confirmed.length).map(a => () =>
  agent(
    `${RULES}\n\nAPPLY these CONFIRMED documentation corrections. They have already ` +
    `survived an adversarial check - do not re-litigate them, just apply them faithfully ` +
    `and precisely, in the house style (strike the wrong claim, write the correction ` +
    `beneath it with the date and the evidence).\n\n` +
    `⛔ MARKDOWN ONLY. If a correction would require editing code, SKIP it and say so.\n\n` +
    JSON.stringify(a.confirmed, null, 1),
    { label: `apply:${a.key}`, phase: 'Apply' }
  )
))

phase('Report')
const summary = await agent(
  `${RULES}\n\nSummarise this documentation truth pass for the project owner. ` +
  `Be concise and concrete: what was factually WRONG in the docs, grouped by how ` +
  `badly it could have misled a fix. Name the worst offenders. Then state plainly ` +
  `what remains UNVERIFIED and would need a game launch.\n\n` +
  `CONFIRMED FINDINGS:\n${JSON.stringify(all, null, 1).slice(0, 60000)}\n\n` +
  `APPLY LOG:\n${applied.filter(Boolean).join('\n---\n').slice(0, 20000)}`,
  { label: 'synthesise', phase: 'Report' }
)

return { clusters: all.length, confirmed: total, summary }
