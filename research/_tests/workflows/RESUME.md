# Parked adversarial / sweep passes — 2026-08-16

Three multi-agent passes were run today. Their scripts are saved beside this
file so they can be re-run in a future session; the run IDs are **session-local**
and will NOT resume after a restart, so re-run from the script instead.

| pass | script | status |
|---|---|---|
| Documentation truth pass | `sc4-doc-truth-pass-wf_a2e9f93e-7d1.js` | **COMPLETE** — 111 findings confirmed, 73 corrections applied across 10 markdown files |
| Open-issue triage | `sc4-open-issue-triage-wf_fd5479c1-151.js` | **COMPLETE** — 14 adjudicated: 4 closable, 3 already done, 3 need a launch, 4 still open |
| Simulator defect sweep | `sc4-simulator-defect-sweep-wf_4c47ee5d-a5a.js` | ⛔ **STOPPED MID-RUN** by user request — pick up here |

Re-run any of them with:

    Workflow({ scriptPath: "_tests\\workflows\\<script>.js" })

---

## The simulator sweep — where it got to and what to do next

It was stopped deliberately, not because it failed. Ten lanes were defined; it
had not reported when it was stopped, so **treat every lane as unfinished** and
re-run the whole script rather than guessing which completed. That is cheaper
than reasoning about partial state, and a partial sweep reported as complete is
exactly the "0 findings without a control" trap the lanes themselves warn about.

The ten lanes: gates-at-all-tiers, pre-scaled-subtree audit, 3x compositor,
the "?" button seed, the text-baseline seed, negative-origin census, font
metrics, 3x regression bisect, crosscheck skips, third-party gates.

### Two seeds it was given, and their status now

**(A) The "?" button.** RESOLVED WITHOUT IT while the sweep was running. It is
not one button - it is TWO stacked (`Query` 0x99887766 above `Route Query`
0x8b96b73e, abutting at y=106, which is the divider line). Route Query's art
exceeds its window in STOCK (design 36x21, art 37x23), so the overhang scales:
+1/+2 at 1x becomes +3/+6 at 3x. See #172.

**(B) The high text baseline / Mayor Rating.** STILL OPEN and now sharpened -
see below. This is the lane worth resuming first.

---

## ⚠ THE MOST IMPORTANT THING TO CARRY FORWARD

**The Mayor Rating bar and the City Opinion Polls bars are NOT a smoothing
regression.** They looked the same in the 1.5x screenshot taken BEFORE the
#175 smooth pass existed, and they look the same after the trend-bar ramp was
excluded from smoothing. Two changes, no movement.

That makes the smoothing work a dead end for this symptom, and it means the
1x-vs-1.5x comparison is NOT the experiment. The experiment is **1.5x vs 2x/3x**,
because those tiers are user-confirmed and were never touched by any of today's
art work.

What is known:
* `cSC4WinTrendBar`, clsid `0xAA5C2F86`, Draw `0x7BF0A0`, vt `0xABA430`.
* It is **code-bound**: `{46A006B0,14015580}` (a green-to-red LOOKUP GRADIENT,
  99x101 at 1x - not a groove) and `{46A006B0,14015584}` (the trend arrow strip,
  magenta-keyed, 42x9). Pushed in by the polls controller at `0x7ED4AC` via
  `SetImages`. **ZERO `.UI` refs**, so no corpus scan can find them - which is
  why they were missed by every offline gate.
* Per SC4-UI-ENGINE.md: sized by its ART's pixel size, drawn CENTRED in the
  window (`x = L + (winW - imgW)/2`); the fill marker is `fraction x (imgdim-1)`
  and bands are `imgdim/3`. **Content scale = art size only.**
* That last line is the lead: if the bar is sized from art and centred, then a
  1.5x window around 1.5x art should be self-consistent - so either the art and
  the window disagree, or `imgdim/3` does not divide cleanly at 1.5x.
  `101 * 1.5 = 151.5` and `9 * 1.5 = 13.5` are BOTH fractional. That is the
  same half-pixel family as the strip step-extra.

**Do this first, before any build:** flip to 2x or 3x and look at the same two
panels. If they are correct there and wrong at 1.5x, it is the fractional
`imgdim/3` and the arithmetic above is where to look. If they are wrong at
EVERY tier, it is not a scaling defect at all and the whole family is the wrong
place - check stock with `Set-StockCompare -Mode Stock`.
