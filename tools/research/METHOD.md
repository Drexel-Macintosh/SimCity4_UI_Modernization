# METHOD — how this project is allowed to work

**This is a NORTHSTAR file, not a reference file.** The other docs say what
SC4 *is*; this one says how we are permitted to find out. It was written
2026-07-30 after a real discipline lapse (§6), on the user's instruction:

> *"update your northstars to INCLUDE using all of your documentation /
> backward decompiling similar to an SDK guide that provides instructions.
> If we have to do something new / novel document it for future use!"*

Three rules, in order. They are not advice.

1. **THE DOCS ARE THE SDK.** Maxis shipped no UI SDK, so we wrote one from
   measurement. Before touching any UI element, the element's own section is
   read and quoted. An answer already in this repo is not allowed to be
   rediscovered by experiment.
2. **DECOMPILE FOR INSTRUCTIONS, NOT FOR CLUES.** The exe is the manual.
   Read the function, name the constant, prove it with the byte pattern —
   then patch it. A screenshot is never evidence about what the code does.
3. **NOVEL WORK GETS WRITTEN DOWN IN THE SAME SESSION.** Anything that had
   to be invented — a new mechanism, a decoded function, a failed approach
   with a real mechanism behind it — is written back before the session
   ends, in the file §3 routes it to. A discovery that only exists in chat
   is a discovery we will pay for twice.

---

## THE LOOP - BOTH ENDS ARE MANDATORY (user order, 2026-07-31)

> "when you get a bug to fix you first compare it against our lessons learned
> and SDK and other documents" ... "after you fix each bug you update the
> documentation."

**INTAKE - every bug starts here, before any theory, agent or build:**

1. `python tools\sdk\lookup.py <window id | art instance | script instance>`
   - our lists + comments, the declaring script + its 1x design size, what we
     stage at every tier, who wins the load order, everything already written.
2. `TRIAGE.md` section 1 - match the SYMPTOM to a solved family. Most defects
   are a repeat and the cure is already named.
3. `MECHANISM-GENERATIONS.md` - is this family on an older generation?
   `REGRESSION.md` - has this exact thing been fixed (or refuted) before?
4. ONLY THEN measure; only after measuring, build.

**OUTTAKE - every fix ends here, in the SAME session, before moving on:**

1. `VERSION-HISTORY.txt` - what changed and WHY, including what was REFUTED.
2. `_tests\REGRESSION.md` - expected log lines, acceptance, trap signature,
   revert. Update `Test-DatIntegrity.ps1` EXPECTED in the same change as any
   entry-count change.
3. The mechanism doc (`SC4-UI-ENGINE.md` or the family's own file).
4. A new `TRIAGE.md` symptom row if one was earned; a new LAW in the laws
   memory if one was earned; `HANDOFF.md` for current state.
5. **Correct everything the fix proved wrong.** Say "refuted", name the
   replacement, and leave the old claim visible with its correction - a stale
   note left standing is the next wrong theory. (On 2026-07-31 four theories
   died on one window because notes outlived the code they described.)

**A fix is not done when the code works. It is done when the next reader
cannot repeat the mistake.**

## 0. THE SDK LOOKUP COMES BEFORE EVERYTHING

    python tools\sdk\lookup.py <window id | art instance | script instance>

The consult order below ("our docs -> SDK headers -> live instruments ->
disassembler -> a shipped experiment") is right, but executing step one used to
mean grepping six files by hand, which is why it was skipped under pressure.
This runs the whole of step one in one call, from LIVE sources, and it refuses
to quote the frozen `_HANDOFF-*` doc snapshots (verified stale: they still call
Create Disaster "UNSOLVED"). It also labels `_incoming/` agent output as leads
rather than evidence. Run it, THEN follow the order below.


## 1. THE INSTRUCTION HIERARCHY (consult in this order — never skip up)

| # | Source | What it answers | Cost |
|---|---|---|---|
| 1 | **This repo's docs** (§3 routing table) | "Has this already been solved / already failed?" | seconds |
| 2 | **The SDK headers** `vendor\gzcom-dll\` | "Does an API already exist for this?" — `cIGZWinText::SetWinTextFlag`, `cIGZFont::CalculateWordsToFitInWidth`, `FitWindowToText` were all sitting in headers while we guessed | seconds |
| 3 | **The live instruments** (MWKID / VWKID / BHDR / POPKID / RGKID / DPROBE / `LiveDumpMs`) | "What is actually on screen right now, and what are its rects?" | one launch |
| 4 | **The disassembler** (§4) | "Where does this number come from, and in what encoding?" | minutes, offline |
| 5 | **A shipped experiment** | Last resort — and only with a stated hypothesis, a predicted log line, and a revert plan | a whole build + a user test |

Level 5 is the expensive one and it is the one we reach for when levels 1-4
were skipped. Every one of the three failed ordinance-popup builds was a
level-5 action taken while a level-1 fact (`1000 − textWidth`, already in
`BUDGET-DETAIL-ANATOMY.md` §1) and a level-2 fact (the SDK's own wrap API)
sat unread.

### ⛔ 2026-08-06 — THE WORST LEVEL-1 SKIP YET (#143)

A level-5 build shipped a change that **level 1 had already evaluated and
rejected in writing, in the row describing the very tool being edited**:

> `README.md`: *"Nearest-neighbor is the default and the right answer; the HQ
> scaler was rejected (blurs pixel art, **fringes the magenta colorkey**)."*

Making `--hq` automatic turned the user's Mayor Rating bar pink within one
launch — the documented failure, verbatim. **Three separate level-1 documents
held the answer** and none was consulted:

| level-1 source | what it already said |
|---|---|
| `README.md` upscale row | HQ was tried and rejected; it fringes the colour key |
| `tools\upscale\VERIFY.md` | the "0-new-colors check" — NN introduces **no colour the source lacks**, which alone refutes the resampler as the cause of a WHITE line |
| `tools\itemicons\rebuild_namicons.py` | already carried `snapped` / `non-div4` counters — the real law (`/4` divisibility), already implemented for one package |

**THE ADDITION TO THE HIERARCHY: before editing a tool, grep the docs for that
tool's own name.** Not the symptom — the *component*. The symptom search
("white line", "seam") returned nothing; `upscale` returned the answer in one
hit. When you are about to change a default, assume someone already chose it
deliberately and go find out why.

**AND: prefer the argument that needs no experiment.** "Nearest-neighbour only
copies source pixels, so it cannot create a colour the source lacks" is a
one-sentence structural refutation available at level 0 — no doc, no
instrument, no launch. It was skipped in favour of a plausible story about
row-duplication patterns. *When a hypothesis can be killed by a property of the
algorithm, kill it there.*

**AND: a comment is not code.** The first revert rewrote the comment block
above `if (!hqExplicit) hq = ...` and left the statement. The tool went on
printing `Mode : high-quality` and rebuilt the entire tier wrong a second time.
Law 54's twin: **a log line that contradicts your edit means the edit did not
land** — read the tool's own banner, not your diff.

---

## 2. PRE-FLIGHT — the canonical checklist

`HANDOFF.md` and `README.md` both point here. Before any fix to any UI
element:

1. **Re-read the element's own section** — `tools\research\SC4-UI-ENGINE.md`
   plus the element's anatomy doc (§3). **Quote it in the plan.** If nothing
   is written about it, say so explicitly — that is itself a finding, and it
   means §5 applies when you are done.
2. **Check the FAILED-ATTEMPTS table** for that element. If the idea is
   already in it, it is not a new idea.
3. **Do we have a STOCK capture of this exact element?** If not, get one.
   A defect that also exists at stock is not our defect
   (`_tests\captures\stock-budget\STOCK-REFERENCE.md`).
4. **Measure the live rects** with the dump instruments. Never infer
   geometry from a screenshot (`feedback-sc4-measure-dont-infer`).
4b. **ASK WHO *COMPUTES* THE VALUE, NOT ONLY WHO PAINTS IT** (law 49, added
   2026-08-03 after #57 cost **six** failed patches — v2.50.0, v2.51.0,
   v2.52.0, v2.54.2/.3/.4; *count settled 2026-08-03, earlier recounts said
   four then five and both dropped v2.51.0*). A rect you can read is an
   **output**. Before patching it, find the code that *wrote* it — for a
   child window that means finding its **allocation site** (a whole-`.text`
   scan for the entry allocator; #57's had exactly one call site each), and
   whoever allocates it is whoever lays it out. ⚠ **A constant that no
   instrument ever prints is still a constant**: #57's six-constant, 110 px
   right-margin budget was invisible to every probe we owned because every
   probe printed resulting rects. If a family survives a second fix, stop
   probing the output and disassemble the BUILDER.
5. **State the stock relationship as MATH** — `value = round(stock × f)` or
   an anchor formula — and show it reduces to stock at `f = 1`. If it cannot
   be written as math, it is a guess, and it will not survive the other
   tiers (1.5x / 3x) even if it looks right at 2x.
   ⚠ **Reducing to stock at `f = 1` is NECESSARY BUT NOT SUFFICIENT** — every
   failed #57 patch the oracle models did, byte-exactly (*that is three of the
   six: v2.54.2/.3/.4. The other three were field-level writes and are not
   candidates*). Prove the form at `f ≥ 1.5`.
   ⚠ **And if the thing you are sizing must CONTAIN RENDERED TEXT, `round(stock
   × f)` is the wrong form** (law 48): ink grows ×2.13 per doubling, not
   ×2.00, so size the box from the FONT. Tier-math still governs geometry and
   art; it does not govern a text box.
5b. **ONE NUMBER, ONE GATE** (law 47). If two gates could certify this fix,
   reconcile them onto a single target **before** building, and make the
   loser's target unreachable — otherwise whichever runs last decides what
   ships.
6. **Then** write code. After it ships, **verify from the log**, not from
   optimism — the startup site counts and the per-fix expected lines in
   `_tests\REGRESSION.md`.
7. **Write back** what was novel (§5) before the session ends.

---

## 3. DOC ROUTING — where a fact lives (and where a NEW fact goes)

Write the fact where the next person will look for it, not where it was
discovered. One fact, one home; everything else links.

| Kind of fact | Home |
|---|---|
| How the engine behaves in general — window model, widget classes, `.UI` format, art binding, HTML text engine, placement/timing laws, exe VAs | `tools\research\SC4-UI-ENGINE.md` (the SDK guide) |
| **A symptom → family → first-move mapping** | `tools\research\TRIAGE.md` (the index the standing order routes every new defect through — a law that changes how you *triage* belongs here as well as in the LAWS row below) |
| Anatomy of ONE panel family — window tree, builder VAs, constants, failed attempts | that family's doc: `BUDGET-DETAIL-ANATOMY.md`, `GOD-MODE-FLYOUTS.md`, `MAYOR-MODE.md`, `DYNAMIC-CONTROLS.md`, `REGION-SWITCH.md`, `ITEMICONS.md`, `UI-ART-BINDING.md`, `FONTS-AND-DIALOGS.md` |
| A rule that decides future fixes | `README.md` → *LAWS* (short form) **and** `_tests\REGRESSION.md` → *LAWS MINTED* (numbered, with the regression it cost) |
| Per-fix history, expected startup/log lines, trap signature | `_tests\REGRESSION.md` |
| A test axis a bug escaped through | `_tests\SCENARIOS.md` |
| Current state, what is open, standing constraints | `HANDOFF.md` |
| The next in-game sitting as an ordered script | `_tests\RUN-SHEET-NEXT-SESSION.md` |
| Work in progress by an agent, audit digests, bug intake | `tools\research\_checkpoints\` (**never** the scratchpad — it gets wiped) |
| A third-party mod whose data we override | `tools\research\UPSTREAM-*.md` (standing order: every override gets a report) |
| Shipped behaviour change | `VERSION-HISTORY.txt` |
| How we are allowed to work | **this file** |

---

## 4. THE DECOMPILATION PLAYBOOK (level 4)

Binary: `SimCity 4.exe` **1.1.641.0 Steam (x86, 4GB-patched)**,
ImageBase `0x400000`, **file offset = VA − 0x400000**. All disassembly is
**offline** (capstone 5.x; Unicorn when a value must be emulated rather than
read) via `tools\research\scripts\disasm.py` / `exe_scan.py`. We never
attach a debugger to the elevated game, and **we never modify the exe on
disk** — every patch is applied in memory at launch by `CodePatches.cpp`.

**Working a constant, start to finish:**

1. **Find the consumer, not the number.** Locate the builder function for
   the window (the instruments give the window id; the id-create call gives
   the VA). Read the function top to bottom before touching anything.
2. **Name every immediate** in that function — x, y, width, margin, id.
   Write them into the family's anatomy doc as you go, with VAs.
3. **Check for TWINS.** The same create often exists twice (group-1/group-2
   branches, one of them dead). A patch that "did nothing" usually hit the
   dead one. *(law 15, 16)*
4. **Check the ENCODING.** The same constant appears as `push imm8`,
   `push imm32`, `lea reg,[reg+disp8]`, `add reg,imm32`. Scanning for one
   encoding finds one copy. `disp8`/`imm8` also cap at 127 — a value that
   cannot encode needs a **runtime pin** instead (§4.1).
5. **Patch with verify-before-write.** Every site carries its expected
   original bytes; a mismatch skips that site and logs it. Count the sites
   and print the count at startup — a DROP in the count is the tripwire that
   the exe or another mod changed under us. Never force.
6. **Express the value as `round(stock × f)`**, never as a 2x literal, so
   the same table serves 1.5x and 3x. Log every imm8 clamp.
7. **Record the site table + the startup line** in `REGRESSION.md` so the
   next session can tell a regression from a rebuild.

### 4.1 When the exe cannot be patched — the runtime pin

A pin corrects a value the game recomputes. Rules paid for in regressions:

- It runs **on the sweep**, not inside a change-only dump branch — the game
  re-lays the window per refresh. *(law 18)*
- Its pairing/identification rule **must not depend on the state the pin
  exists to correct** — "find the slider nearest the unpinned notch" can
  never match. Pair by **id arithmetic**. *(law 19)*
- **Idempotent, position/size only, no scale record.** A record outlives the
  state that matched it, and the record-owning re-pass will double whatever
  the game lays into that window later. *(law 14 — this is why
  `0x0423278F` is permanently banned from `kCityDialogIds`)*

### 4.2 What the exe will not tell you

Text laid out once at creation does not re-wrap: not from a width change,
not from re-applying the same caption (it early-outs), not from
`FitWindowToText`, not from clear-and-restore. *(law 21)* When behaviour is
owned by a class rather than a constant, the answer is in the **SDK headers**
(level 2) or in pre-computing the input ourselves — not in another byte.

---

## 5. THE WRITE-BACK CONTRACT (rule 3, made concrete)

**Novel** = anything that was not already in this repo: a decoded function,
a new mechanism, a new failure mode, a tool, a workflow, or an approach that
failed for a reason worth knowing. Bug fixes that follow an existing pattern
are not novel — they are `REGRESSION.md` entries.

For each novel thing, in the file §3 routes it to:

```
WHAT it is            — one sentence, in the reader's vocabulary.
EVIDENCE              — log line / VA / script path+line / capture. If it is
                        inference, label it HYPOTHESIS and do not promote it
                        without measuring.
WHY it is true        — the mechanism, not the symptom.
HOW to use it         — the reproducible steps or the site table.
WHAT IT COST          — the wrong models tried first, so nobody re-walks them.
```

Two non-negotiables:

- **Failed attempts are documented with their MECHANISM.** A failure list
  without mechanisms just gets retried in a different order. The
  `BUDGET-DETAIL-ANATOMY.md` §POPUP table is the model.
- **A dead end is a permanent entry.** Every anatomy doc carries a DEAD ENDS
  section; it is cheaper to read than to re-derive.

Same-session rule: write it back **before** the session ends. Chat is not
storage — this repo is.

---

## 6. WHERE THIS IS GOING — THE OFFLINE MODEL (user direction, 2026-07-30)

> *"You built a simulator before — you should have enough data points now to
> essentially map out the entire game."*

Correct, and it is the logical end of rules 1-2. We already own every
ingredient:

- an **offline emulation harness** (capstone 5.x + Unicorn) that was used to
  crack the flyout hit-test router without launching the game;
- **~130 identified exe VAs**, the builder functions for the budget family,
  the god/mayor flyouts, the label/band/stacker primitives;
- the **art families** (a band set's PNG dimensions *are* the dialog's
  geometry) and the 330 `.UI` scripts;
- the **live oracle** — MWKID/VWKID/BHDR/POPKID/RGKID dumps of real rects to
  check any prediction against;
- **stock captures** at 1024x768 to anchor `f = 1`.

**The target:** a machine-readable map of the game's UI that can predict a
panel's window tree and rects at any factor **without launching the game**,
so an in-game session becomes CONFIRMATION rather than discovery.

Staged, each stage useful alone:

| Stage | Deliverable | Kills |
|---|---|---|
| 1 | **Builder census** — every call site of the create/label/band primitives, grouped by owning dialog, emitted as a table | "which function builds this window?" guesswork |
| 2 | **Constant map** — every immediate feeding x/y/w/h/margin in those builders, with its ENCODING and its twin, generated not hand-enumerated → `CodePatches` tables become generated data | laws 15 + 16 (missed encodings, missed twins, missed second code path) — the two most expensive bug classes of the whole project |
| 3 | **Layout emulation** — run a builder under Unicorn with stubbed window/font APIs, recording every create/SetArea; output = predicted tree + rects for a given factor and font metrics | "measure by shipping a build"; predicts UNSEEN panels |
| 4 | **Diff harness** — predicted tree vs the live dump vs the stock capture, as a `_tests\` suite | silent regressions; makes tier generality (1.5x/3x) provable offline |

**First application, and the acceptance test:** the ordinance description
popup. Stage 3 on `sub_779660` answers §POPUP question 2 outright — emulate
the call with the real font metrics and READ the width the layout wraps
against, instead of shipping a fourth guess. If the model reproduces the
measured 795x75 (City Lottery) and 750x25 (Smoke Detector) bodies, it is
trustworthy; if it does not, the model is wrong and we learn that offline
for free.

Standing rule for the build: **the model is never the authority — the live
dump is.** Every prediction ships with the measurement that confirmed it, or
it is labelled `HYPOTHESIS` (§ evidence rules, `SC4-UI-ENGINE.md`).

---

## 6A. THE GAME IS SIMULATED — USE THE MODEL BEFORE YOU TOUCH THE GAME

**User order, 2026-07-30 night, after two shipped regressions in one evening:**
*"ADD INSTRUCTIONS ABOUT HOW YOU HAVE THE GAME SIMULATED AND EVEN SMALL
CHANGES CAN HAVE RIPPLES TO ALWAYS REVIEW YOUR DOCUMENTS LIKE YOU'RE BUILDING
A UI SDK."*

**You are not reverse-engineering blind. You have a working offline model of
this game's UI**, built 2026-07-30 and living in `tools\uimap\`:

| Instrument | What it answers | Cost |
|---|---|---|
| `census.py` / `constants.py` | which function builds a window, and every geometry constant it feeds, with ENCODING and TWINS | minutes, offline |
| `emu\emu_layout.py` | runs the game's OWN layout code under Unicorn: predicts a window's tree + rects at any factor | minutes, offline |
| `diff\diff.py` + `_tests\Test-UiMapDiff.ps1` | predicted vs live vs stock, at f = 1.0/1.5/2.0/3.0 | seconds |
| `tools\flyout-sim\` | the older per-function emulators (hit-test, plot, gauge) | minutes |

**So the order of operations is: model first, game last.** Every question of
the form "what happens if I change this?" has an offline answer that costs
minutes and cannot break anything. Shipping a build to find out costs a
rebuild, a deploy, the user's play session, and — twice on 2026-07-30 — a
broken UI the user had to report.

### THE RIPPLE RULE — a constant is never alone

The sub-flyout failures of 2026-07-30 night are the canonical example, and
both directions of the same coupling:

```
[+0xEC] = artHeight - 2 x [+0xE8]      the bar's 9-slice middle segment
  stock            53 - 2*25  =   3    correct
  constants only   53 - 2*50  = -47    NEGATIVE -> renders as a sliver
  art only        106 - 2*25  =  56    ~19x too tall
  both            106 - 2*50  =   6    = 2 x stock
```

One `push imm8` moved, and a value 200 bytes away in a different subsystem
went negative. **Before changing ANY constant, ask the model: what else reads
it, and what is computed FROM it?** `constants.json` has the consumers;
`emu_layout.py` will run the arithmetic for you. Both answers are free.

Corollaries paid for in regressions:
- **A shared setter serves more than one builder.** `vf10` is called by both
  the sub-flyout builder and the first-level flyout builder; the second is
  already scaled elsewhere. Discriminate by RETURN ADDRESS (law 16 again).
- **Art and code constants can be a matched pair.** Neither half is shippable
  alone when one is computed from the other. If a fix has two halves, they
  ship together or not at all.
- **"It worked for panel X" is not evidence about panel Y.** Data pre-scale
  cured the advisor strip and BROKE the city HUD, because the HUD is composed
  and re-laid at runtime. Check the construction type (§4.7 of the engine
  doc), do not reason by analogy.

### BLAST RADIUS vs PRIZE — the check that was missing

**State the prize and the blast radius before writing code, and refuse the
trade if it is upside-down.** On 2026-07-30 the prize was a **1-2 frame
flash (20-36ms)** and the change was **rebuilding how the menus are
constructed** — machinery that working flyouts depend on. That is a bad trade
however well it is engineered, and it broke the user's UI twice.

Ask, in order:
1. What exactly does the user get? (Quantify it. "20ms" is a different
   proposition from "the panel is unreadable".)
2. What breaks if I am wrong? (A cosmetic residual, or a menu that no longer
   opens?)
3. Is there a SMALLER mechanism that already exists? Prefer tightening an
   existing, proven path over building a new one. (For the flash: the buffer
   force-recreate already exists — moving it earlier is a timing tweak inside
   proven machinery, not a new construction pipeline.)
4. Can the model answer it offline first? (§6A. Yes, nearly always.)

### TREAT THESE DOCS AS A UI SDK YOU ARE WRITING

The user's framing, and it is the right one: **we are writing the SDK Maxis
never shipped.** That has consequences for how you work:
- An SDK author does not guess an API's behaviour — they read the reference,
  and if it is missing they write it after measuring.
- An SDK author does not change a shared primitive without enumerating its
  callers. `census.py` enumerates callers.
- An SDK author documents the failure modes beside the feature. Every
  anatomy doc here carries a FAILED-ATTEMPTS table and a DEAD ENDS section
  for exactly that reason.
- **Re-read the reference before every change, including the parts you
  wrote.** Three times on 2026-07-30 the answer was already in these files
  and was not read: the `1000 - textWidth` note, the flash-cure table, and
  the `[+0xEC]` coupling warning that had been handed over hours earlier.

### YOUR OWN INSTRUMENTS CAN LIE — audit them before believing a timing

Added 2026-07-30 late, after both halves of one night's diagnosis were bent by
our own log lines. Two failure shapes, and they recur:

1. **A line that logs a STATE, not an EVENT, will lie about WHEN.** The sweep's
   `SUBHOOK ... installed` prints on every sweep while a menu is open (194
   times in one session) because the install is gated *separately*, above it.
   Read as an event it says "installed at +159 ms"; the truth was that the
   *claim* changed at +159 ms and the install had happened elsewhere.
   `SUBCLAIM` — which fires only when the field actually changes — was the
   honest signal. **Before timing anything from a log line, read its printf and
   confirm it is inside the branch that DOES the thing.**
2. **A line that logs an INPUT will not tell you the OUTPUT.** `DCBUF` prints
   the incoming blit request; the widen/upscale transform runs *after* it. Its
   `dst(205,..) src 53x3` looks exactly like "the bar drew at 1x" and still
   prints, unchanged, after the bug is fixed.

The generalisation, and it is the same lesson as the FLASHSET blind spot
(§4.7): **an instrument is a claim about the code, and it decays.** When a
measurement surprises you, re-read the printf before re-reading the world.
Corollary that paid off the same night: a defect that appears only on the FIRST
use of a session is almost always an **uninitialised latch**, not a race —
later uses look clean because they inherit state, not because they are faster.

### THE LAW THIS SESSION EARNED: a null is not evidence until the instrument is proven able to see

**Six probes on 2026-07-30 returned nothing, and every single null was a blind
spot rather than a fact:**

| # | probe | why its null meant nothing |
|---|---|---|
| 1 | full-screen windows | walked ONE root; the suspects lived under the other |
| 2 | same, both roots | only 2 levels deep; the suspects were deeper |
| 3 | `FLASHSET` | sat 52 lines below the `continue` that skipped every flyout |
| 4 | `VisTrace` v1 | logged only visibility FLIPS — a window CREATED on the event was silently baselined |
| 5 | `EdgeBlt` | the class-Blt hook was not installed yet (it installs lazily on the first flyout) |
| 6 | `EdgeBlt`, armed | the UI buffer class **never composites to the screen** — every dest is panel-sized, so a full-screen border could not appear in principle |

**THE RULE: before reporting "X does not happen", state the positive control —
what WOULD this instrument have printed if X did happen, and has it ever
printed that?** #5 and #6 are the sharpest: the same detector, same zero, two
completely different reasons, neither of them "the thing doesn't happen".

Cheap positive controls that work:
- **prove the instrument ran at all** (a `primed`/heartbeat line with a count:
  `VIS primed - 840 windows baselined` is what made #4's null trustworthy once
  the creation gap was closed);
- **prove the hook is installed** before believing what it did not see;
- **prove the surface/scope can contain the target** — dump the destinations
  the hook actually sees (that single check is what exposed #6).

And the corollary for reporting: **say which of your negatives are structural
and which are measured.** A structural null belongs in the write-up as "could
not have seen it", never in the evidence column.

## 7. WHY THIS FILE EXISTS

2026-07-30 evening, verbatim:

> *"I just feel that you haven't been referring to your own playbooks and
> testing. It's like a regression of discipline when you should be checking
> your own documentation THAT YOU CREATED."*

He was right, and the evidence is specific:

- `BUDGET-DETAIL-ANATOMY.md` §1 — written **that same day** — already
  recorded that `sub_779660` sizes its window as `1000 − textWidth` (the
  `push 0x3e8` at `0x77971A`). That is the prime suspect for the ordinance
  popup's wrap width. **Three builds** were spent without testing it,
  because the doc was not re-read.
- `STOCK-REFERENCE.md` carries the standing directive *output = stock
  scaled, judged by geometry* — yet three fixes were attempted on the one
  budget element that has **never been captured at 1x**.

Both failures were free to avoid. That is what makes them worth a northstar.

---

## THE CONTROL BEATS THE INSTRUMENT (2026-08-06, #148)

Ten theories were tried against "the sun and the moon have lines on them". All
ten were wrong, and several were backed by clean arithmetic and passing gates.
What ended it in minutes was a different screenshot: **one of five identical
buttons wrong**, with four working siblings beside it.

- *"The sun and the moon are wrong"* is consistent with a hundred mechanisms.
- *"One of these five identical buttons is wrong"* is consistent with almost
  none — and the difference between it and its siblings (an odd left edge) IS
  the cause.

**When a defect resists, stop building instruments aimed at the broken instance
and go find a working sibling.** Ask the user for that case explicitly; it is a
cheap request and it outperformed a day of tooling.

### Then pick the smallest lever

#148 was diagnosed correctly and then fixed twice with the wrong lever, both
reverted the same day:

1. **Moving** the control fixed it — and slid a 21-face grid, the advisors, the
   budget rows and the bottom dock. *A fix that moves things is judged by its
   densest neighbourhood, not by the case that reported the bug.*
2. **Resizing the art** fixed it — and broke the flyout thumbnails, because the
   strip items are created at RUNTIME, appear in no `.UI`, and still bind art by
   TGI. *A `.UI` edit is scoped to that `.UI`; an art edit is scoped to the
   whole game.*

The cure was the third lever: change the **size** of leaf windows only.
Nothing moves, nothing else consumes it, and it is a no-op at integer factors by
construction.

## COUNT THE NUMBERS THE MECHANISM HAS, THEN COUNT THE ONES YOU SCALED (#154)

A `blttype=normal` blit is decided by **three** numbers: the bitmap, the
`imagerect` crop, and the window. v2.97.0 scaled two of them and shipped a
dialog whose row stripes painted 285px of a 428px window. The rule *"never
double art without doubling the imagerect"* was already written in
`SC4-UI-ENGINE.md` §3.3 — knowing it did not help, because the code path that
breaks it never asks the question. The builder scales a rect only when its test
says "this control's art was scaled", and that test read a plan computed from
the **stock** art store alone, so art supplied by a MOD is permanently
classified as unscaled there however thoroughly we scale it elsewhere.

Two transferable habits:

1. **Enumerate the mechanism's inputs before enumerating your changes.** Write
   the three (or four) numbers down and tick each. "I scaled the window and the
   art" reads like completeness and is a two-thirds fix.
2. **When a test asks "did X happen?", check that it can see every way X
   happens.** `art_plan` answers "did the art scale?" for one supplier. A
   second supplier existed, and the answer was silently "no" forever.

### THE GATE FAILED THE SAME WAY, WHICH IS THE WORSE HALF

`gate_tp_bmp_fit.py` **passed the broken build.** It read the window and it
read the bitmap and never the crop between them — two of three, again. A gate
that measures a subset of a mechanism's inputs does not "partially cover" it;
it certifies exactly the failure it cannot see. **When a gate checks a
mechanism, make it read every input, and if it cannot, make it print which one
it is not reading** so the next reader knows the green is conditional.

Its first repair then asked the wrong third question — *"does the crop still
cover the same fraction of the BITMAP?"* — which flags a glyph whose bitmap
snapped 20→32 while crop and window both went 20→30, two transparent pixels
undrawn and nothing wrong. The question that decides pixels is **how much of
the WINDOW gets painted**. Getting the third number into the gate was not
enough; it had to be the third number *asked about the right thing*.

**And the negative control must be the artefact that actually shipped.** The
script was extracted back out of the DEPLOYED dat and fed to the fixed gate:
48 findings, in plain language. A control built by hand-breaking the current
build proves the comparator works; a control built from the thing that was
wrong on the user's screen proves it would have caught THIS.
