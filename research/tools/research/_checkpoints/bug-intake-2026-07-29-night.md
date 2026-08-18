# User test reports, 2026-07-29 night (post v2.23.3) — triage

TWO ARE OUR OWN REGRESSIONS from tonight's fixes. Own them.

## 1. U-Drive-It picker icons "duplicated NOW" — OUR REGRESSION (v2.23.1)
Was fine before we touched it. CAUSE: we static-doubled the pickers
I-4bf325e8 / I-abfaef15 (root 0xCBF32603) in the text-sweep batch, but their
icon strip {46A006B0,EA32F104} has NO 2x asset — the builder logged
`LEFT1X (no 2x asset in upscale preview set)`. Doubled cells + 1x multi-state
strip = the EXACT Grutzehaus mechanism (GZWinBtn slices state as
imageWidth/4). FIX: generate 2x for EA32F104; then audit EVERY other LEFT1X
in the dialog-static report the same way. Data-only.

## 2. My Sims faces not filling the square — KNOWN, task #47
Runtime-painted portraits (TGI-less, imagerect 36x41). Expected; no new info.

## 3. My Sims car + bike option pictures don't fill their window — INVESTIGATE
Style thumbs {4C06F888,106B0000} + {4C06F888,10102700} (42x42). v2.22.2 added
the detail roots to SCALED_WINDOW_IDS which SHOULD have pulled these out of
UNSCALED-untouched. Black square + small icon = art still not covering.
MEASURE: their refmap action in the CURRENT build; if staged 2x, the node is
runtime-painted (task #47 family) instead.

## 4. Green circle should dock to the 2nd round bubble (U-Drive-It) — task #48
Mayor-flyout selection ring on the wrong button. Needs the MCAL measure-only
pass; no alignment marker exists to derive from offline.

## 5. Sub-flyouts not 2x / pictures not seated / clicks only on the right —
OUR REGRESSION (v2.22.1 crash guard) — deliberate but incomplete.
Those three symptoms are EXACTLY what the disaster container/strip hooks fix
(buffer force-recreate + item-field doubling + [0xE0] claim widen). The
KNOWN-MENU GATE withholds them from any menu not in kParents — it stopped the
Earned Cars crash but leaves U-Drive-It's sub-flyout unscaled. Log signature:
`SUBSKIP container 0x8A6E61E0`. FIX = the proper opt-in the user asked for
twice: measure THIS menu's strip (StripDump/DGP-OPEN + item fields), then add
its root to kParents. Do NOT just widen the gate — that is what crashed.

## 6. Graphs still broken — INVESTIGATE (art shipped, symptom persists)
0x8A8B5B72 went into SCALED_WINDOW_IDS at v2.22.3, shipped in the 506-dat.
TWO things in the screenshot: the chart line/axis labels small (task #47
code-painted class, known) AND an unpainted plot background + misaligned
bottom band (NEW). MEASURE: DPROBE 0x8A8B5B71/72/0x0A4A8176 live; confirm
which script copy is live — audit says I-6bc9065a with I-ea2871aa STALE, our
builder edits BOTH, so a stale copy winning the load race is a live
hypothesis for an unpainted background.

## 7. Building Style boxes look incorrect — INVESTIGATE
Rows/checkboxes read 1x-ish with large empty space. The code-created audit
already found ~20 runtime ids under 0xABC619D2 absent from the shipped mod
script (DLL-created, or a newer mod build). MEASURE that dump diff first.
LOAD-ORDER LAW applies; never modify the mod's files.

## CROSS-CUTTING LESSON (add to REGRESSION.md)
**A LEFT1X / no-2x-asset art reference inside a frame we DOUBLE is a BUG, not
a safe fallback.** Both #1 and the Grutzehaus report are this shape. Any
builder deciding "no 2x asset -> leave 1x" must WARN when the consuming frame
is scaled, so it surfaces at build time instead of in the user's game.
