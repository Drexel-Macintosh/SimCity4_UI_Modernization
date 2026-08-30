# `_incoming\` — CLOSED 2026-08-30. The drafts are retired.

This folder held **twenty raw decode drafts** (~580 KB) written by agent
workflows and never edited afterwards: fifteen on 2026-07-31 by three parallel
decodes (`subsystems-01..04` — paint/invalidate, input routing, the `.UI`
grammar, transients and modality; `sdkgaps-01..06` — `GZWinBMP`, the widget
catalogue, the region screen, art binding, the `census.py` blind spots;
`crossfire-01..05` — the task #72 region rating bar decoded four independent
ways), plus five later single investigations (`SHUTDOWN-SPIN`,
`PLAN-104-SHUTDOWN-SPIN`, `SPINPROBE-CAPTURES`, `TIER15X-DASHBOARD`,
`BUDGET-POPUP-X`).

This file used to say they were "RAW: unverified, overlapping, and known to
contain mistakes," that nothing here was authoritative, and that each block had
to be re-measured before it was believed. **That has now been done, and the
drafts are gone.** If you followed an old citation here, the fact it named is
in a canonical doc — see the table below.

## What was done

Every draft was adjudicated **claim by claim**, against the shipping exe
(`SimCity 4.exe` 1.1.641.0, 7,876,608 bytes, ImageBase `0x400000`), the `src\`
tree, `tools\uimap\funcs.json`, the shipped `.dat`s and the live captures —
never against another draft. Agreement between drafts was never counted as
verification (law 34: two blind instruments agreeing is one instrument).

**121 claims: 84 verified, 23 contradicted by re-measurement, 14 unverifiable.**
Eight of the 84 were already canonical word for word and were dropped on the
spot; the remaining **76 named a destination**.

A second, **adversarial pass then tried to refute all 76** from its own
instruments — its own PE reader, capstone, byte scans, a from-scratch PNG
decoder — without being shown the first pass's reasoning.

| outcome | n | |
|---|---|---|
| survived intact | 55 | promoted as written |
| **amended** | 6 | a corrected destination, or a narrowed scope — the usual failure was a draft generalising from a single call site |
| **rejected outright** | 14 | almost none for being *false*: for **not being novel**. The fact was already canonical and the draft was about to re-import it with staler line numbers |
| not a claim | 1 | an endorsement of a sibling note, nothing proposed |

**Net: about half the folder's claims — 61 of 121 — reached a canonical
document.**

## ⭐ The yield was corrections to canon, not new facts

The drafts' real value was exposing places where a **canonical doc asserted
something the binary or the shipping code disagreed with** — which is worse
than a raw draft being wrong, because `TRIAGE.md` routes readers to those docs
as the authority. Every such correction is **annotated in place and dated
2026-08-30**, saying what was wrong and what replaced it, rather than silently
rewritten.

## Where the survivors went

Grep `2026-08-30` in any of these to see what arrived.

| destination | what it received |
|---|---|
| `tools\research\SDK-GAPS.md` | the largest share — vtable-slot and window-flag rows, the `.UI` corpus census and nesting depth, `.UI` root `area=` vs the code-driven message-box placement, and the `cSC4WinAuraBar` §8.3 corrections (shipped art size, the bar's real bidirectional row map, the registry slot, the object fields) |
| `tools\research\SC4-UI-ENGINE.md` | class-row vtables and two mislabelled slots, the private-buffer vs mask correction, the generic image-type framing for the art store, the identification procedure's worked vtable diff, and two caveats on shipped scaling laws |
| `tools\research\UI-ART-BINDING.md` | the `edgeimage` bullet, and three cross-references that pointed at a section that does not exist |
| `tools\research\FINAL-3-PERCENT.md` | the RGKID instrument's per-level sibling caps, and two quotes inlined out of a draft that this doc cited by line number |
| `tools\research\BUDGET-DETAIL-ANATOMY.md` | the empty-ledger popup: its command handler, its jump table, and the `GetFlag(0x1000)` gate |
| `tools\research\METHOD.md` | the null-is-not-evidence law in its strongest form, and a seventh row on the six-probe table |
| `tools\research\SCALING-AXES.md`, `FONTS-AND-DIALOGS.md`, `REGION-SWITCH.md` | one measured correction each |
| `_tests\REGRESSION.md` | task #72 and #106, the BMPX trap signatures with current numbers, and three new laws |
| `tools\uimap\`, `tools\uimap\emu\`, `src\` | where a draft's finding was really a code defect: a stale generator comment, an oracle constant that would have filed a measurement under a point size the game never renders, and comment blocks carrying wrong measurements |

The one live *procedure* in this folder — the 1.5x/3x `lineHeight` capture — was
not a draft and was not retired; it is at
`_tests\LINEH-TIER-CAPTURE-PROCEDURE.md`, beside the probe list that calls for
it.

## What was NOT kept, and why that is the point

Contradicted claims were dropped and are recorded nowhere: a draft that
reasoned correctly from an incomplete measurement, and was overturned by a
better one, leaves nothing behind. Unverifiable claims — mostly inferences with
no stated control — were dropped too. **Do not restore this folder from git
history to "check what a draft said."** Anything in it that was true is now in
a doc that has been measured; anything not promoted was checked and refused.

A future raw agent drop gets its own folder and the same treatment: adjudicate
claim by claim, refute adversarially, promote the survivors, retire the drafts.
