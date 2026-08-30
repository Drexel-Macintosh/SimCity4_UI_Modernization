# START HERE

**SC4UIScale — runtime UI scaling for SimCity 4 Deluxe 1.1.641.**

Research-corpus orientation: what has been reverse-engineered about SC4's UI
engine, what is still unknown, and how research work happens here. For
contributor orientation (build, deploy, standing engineering rules) read
[../START-HERE.md](../START-HERE.md) first; this file is for research
specifically.

**The current version is never pinned in prose — prose rots.** Two sources
cannot rot: `UISCALE_VERSION_STR` in `src\SC4UIScaleDllDirector.cpp` is the
version that stamps the running DLL's log header, and `VERSION-HISTORY.txt:1`
is the newest ledger entry. When any document disagrees with the macro, the
macro is the one that is running.

**This file's own content stops at 2026-08-19.** For anything after that —
including a Graphics Options selector rewrite, a v3.14 flyout state-machine
rewrite, and an open sub-flyout arm-alignment defect (short-count strips like
Sports Grounds and Plazas) — read `UNKNOWNS-AND-NEXT-TARGETS.md` §D.1 first, then the
newest-dated `..\HANDOFF-*.md` in the repo root. Both postdate this file and
are not summarized here.

This file is the entry point. If you have lost everything else and found this,
read it top to bottom and you can continue.

---

## 1. What this is

SimCity 4's interface is hard-coded for 1024×768. This project renders the UI
at 1.5×, 2× or 3× on a high-DPI screen while the world keeps rendering at
native resolution. Two halves that must agree:

- **Data** — enlarged copies of the game's UI art and `.UI` layout scripts,
  shipped as DBPF packages that load after the originals and win.
- **Runtime** — `SC4UIScale.dll`, a gzcom-dll plugin: live window geometry,
  byte-patched layout constants inside the executable (**18 feature families
  across 36 site tables, 295 individual patch sites** — measured 2026-08-30 by
  `tools\uimap\emu\gate_patch_families_combined.py`, which is the only thing
  allowed to state these counts), and render surfaces that must be recreated
  rather than resized.

Nothing modifies a game file. Everything is in-memory, per session.

## 2. Where things are

```
src\            the plugin. SC4UIScale.vcxproj / .sln
tools\          the package generators and the analysis pipeline
_tests\         deploy, integrity and offline gates
_packaging\     public-release build + the checks that gate it
_archive\       superseded process docs. History, not instructions.
```

The touch plugin is a **separate project** in the sibling folder `..\SC4Touch\`
and shares no file with this one. Both folders were one tree until 2026-08-06;
that sharing repeatedly leaked touch content into this project's public
release, which is why the split exists. Do not reintroduce a dependency on it.

## 3. First things to run

```
:: build
msbuild src\SC4UIScale.vcxproj -p:Configuration=Release -p:Platform=Win32

:: deploy (waits for the game to close - NEVER kill it, it runs elevated)
_tests\Deploy-OnGameClose.ps1

:: prove the install matches what was built
_tests\Test-DatIntegrity.ps1
_tests\Test-ThirdPartyGates.ps1

:: offline gates - no game needed, all must exit 0
python tools\uimap\emu\gate_namicons.py
python tools\uimap\emu\gate_patch_families_combined.py
python tools\uimap\emu\gate_advice_rowx.py
python tools\uimap\emu\gate_ordinance_namex.py
python tools\uimap\emu\gate_103_twin_ids.py
python tools\uimap\emu\gate_graphs_banddock.py
python tools\flyout-sim\gate_subnative.py
```

If the exe-pinned gates fail with `fingerprint mismatch`, the game was
reinstalled or re-patched. **Do not just re-pin.** Read
`_tests\REGRESSION.md` → "THE 4GB PATCH SILENTLY BLINDED EVERY EXE-PINNED
GATE" for the procedure: bypass, run the byte assertions, re-pin only if they
all pass, and write down that you did.

## 4. Which document answers which question

| Question | Read |
|---|---|
| A user reported a symptom. Where do I start? | **`tools\research\TRIAGE.md`** — symptom → cause → lever, every row paid for by a shipped fix. Read this FIRST, always. |
| How does SC4's UI actually work? | `tools\research\SC4-UI-ENGINE.md` — the SDK-style reference. The single most valuable artefact here. |
| An in-world visual that is NOT a window (balloons, signs, glows, route dots)? | `tools\research\SC4-WORLD-OVERLAYS.md` — the renderer-side companion of SC4-UI-ENGINE.md, with the 23-row in-world census (every owning system identified) and the two-worlds triage law |
| How should I work on this? | `tools\research\METHOD.md` — measure, don't infer; instruments before theories. |
| What did we already try, and what was refuted? | `_tests\REGRESSION.md` — the laws, the dead ends, and every "measured dead, do not retry". Long, but it is the project's memory. |
| What changed and when? | `VERSION-HISTORY.txt` |
| What must I test before believing a fix? | `_tests\SCENARIOS.md` — the scenario matrix. Five bugs in one session came from one untested axis. |
| What does each shipped package contain? | `tools\packages\PACKAGES.md` |
| Region screen | `tools\research\REGION-SCREEN.md` (197 functions decompiled) |
| Flyouts and their rings | `tools\uimap\SUBFLYOUT-*.md`, `tools\research\GOD-MODE-FLYOUTS.md` |
| Menu icons | `tools\research\ITEMICONS.md` |
| Fonts and text layout | `tools\research\FONTS-AND-DIALOGS.md` |
| Which art is bound how | `tools\research\UI-ART-BINDING.md` |
| We override another mod — what and why? | `tools\research\UPSTREAM-*-REPORT.md`, one per mod |
| Publishing | `_packaging\Build-PublicRepo.ps1` + `Test-NoForeignContent.py` |

Generated files (`REPORT*.md`, `BUILDER-CENSUS.md`, `CONSTANT-MAP.md`,
`coverage-matrix.md`, `package-list*.txt`) are pipeline **output**. Re-run the
generator; do not hand-edit them, and do not treat them as sources of truth.

## 5. Standing rules — these were each paid for

1. **The game runs ELEVATED. Never kill it.** It holds the DLL and the dats
   open. Deploy with `Deploy-OnGameClose.ps1`, which waits.
2. **Never modify game files or another mod's files.** We ship overrides that
   load later, gated on the mod being present.
3. **SC4's plugin scan is RECURSIVE.** A stash folder inside `Plugins\`
   disables nothing. Only an extension rename or a move OUT of the tree does.
   Every "stock" capture taken before 2026-08-05 is contaminated.
4. **Coverage means OUR FILE LOADS LAST for that resource** — not "the
   resource is in one of our packages". Root files load before subfolders.
   Those two questions disagreed for exactly 1 icon in 392.
5. **A package is not finished until it is in `Deploy-OnGameClose.ps1` AND
   `Test-DatIntegrity.ps1`.** Three packages have rotted from this exact
   omission; every one of them looked green.
6. **Never write an ini with a BOM.**
7. **Prove the branch executes before improving what it does.** Read the mode
   out of the live ini and the `installed ... (mode N)` log line, never the
   default in a header. Two correct fixes once shipped on a dead path.
8. **A null is not evidence.** State the positive control — show the
   instrument could have seen the thing — before believing it saw nothing.
9. **If a fix must re-apply every tick, it is a fight, not a fix.** Find the
   game's own path and be correct at birth.
10. **A constant commented "factor-independent" is a claim.** Evaluate it at a
    second tier before believing it. Same for any "permanent" tier split — an
    encoding ceiling is an encoding, not a law.
11. **When a rule is justified by "it is exact", name the factors it is exact
    FOR.** Integer factors hide a whole class of defect: they preserve
    divisibility, so the game's own `width/3` and `width/4` cell divides can
    never mis-cut at 2× or 3×. At 1.5× they mis-cut 31% and 43% of the time.
    Four defects in one session had this exact shape. 2× and 3× cannot
    validate it — only a fractional tier can.
12. ⭐ **NORTHSTAR — TWO QUESTIONS ON EVERY DIAGNOSIS, NEVER ONE** (user order,
    2026-08-06):
    **(a) have we hit this before?** and **(b) is the way we fixed it then
    VIABLE HERE?** If it is, **port that fix** — do not design a new mechanism
    beside it. If it is not, say why in one sentence before writing anything.

    Question (b) is the one that gets skipped. On 2026-08-06 the prior cure for
    the dock minimap (#126: *the "garbage" is our own baked artwork* — strip it)
    was found, quoted, and then a window-shrink was invented on top of it, which
    turned off the stretch blit that fills the recess. Four defects that day
    were already answered in `README.md`, `VERIFY.md`, `BUILDING.md` and
    `VERSION-HISTORY.txt`.

    **Corollary:** when one tier/variant misbehaves and a sibling is confirmed
    fixed, the default hypothesis is **"the known cure never reached this one"**,
    not "this one needs a new cure". Check the gate that decides who gets the
    fix — a factor threshold, a mod gate, an id list. The 1.5× minimap was
    exactly that: `DOCK_NEUTRALIZE_MIN_FACTOR = 2.5` excluded it from a cure
    that already worked at 3×.

17. ⭐ **THE OFFSET-PARITY LAW** (2026-08-13, #152/#153 — it closed two defects
    and named the failing axis on both before either was looked at).
    For `f = p/q` in lowest terms, edge-derived rounding preserves a child's 1×
    offset `d` from its frame **iff `q | d`** — because
    `round((t+d)f) − round(tf) == df` exactly when `df` is an integer, and
    otherwise depends on the **parity of the frame's own coordinate `t`**.
    **At f=1.5 (q=2): even offsets always survive, odd offsets are a lottery.**
    At an integer factor `q=1`, which is why 2× and 3× never show this family.

    | panel | offset | prediction | user's word |
    |---|---|---|---|
    | advisor faces | (2,1) | y odd → 1px HIGH | "high" |
    | My Sim grid | (3,2) | x odd → 1px LEFT | "left" |
    | advisor detail | (2,2) | both even → never fails | correct at every tier |

    **The cure is to SEAT, not to nudge:** place the child at
    `frame + ScaleRound(offset)`, translate only, cap the delta at 1px, and
    assert the integer-factor no-op at the call site. Rejected on measurement:
    an ungated rule moves 456 dashboard windows; `floor()` positions move
    373/531 budget+graphs.

18. **WHEN A BUILD FAILS LOUDLY, VERIFY THE MESSAGE BEFORE BELIEVING ITS
    IMPLICATION** (2026-08-13, #153). `id 0xAA243E23 occurs 0 times` was
    **true**, and the conclusion drawn from it — "so the pairing is wrong" —
    was false. The real cause was a `\b` turned into a literal backspace byte
    by machine-generating a regex through a string template. A correct fix was
    reverted on that. **A guard that fires proves something is wrong; it proves
    nothing about what.** Corollary: do not machine-generate code containing
    regexes.

22. ⭐ **A HEURISTIC THAT IDENTIFIES A STRUCTURE IS SAFE FOR PROTECTING IT AND
    UNSAFE FOR REWRITING IT** (2026-08-14, #156). `CellUnit` guessing "this
    width divides by 4, so it might be a strip" costs nothing when it *preserves*
    divisibility. The same guess used to *re-time pixels* changed **1186 of 2206**
    sheets and displaced an advisor aperture. Derived from the `.UI` that BINDS
    each sheet instead: **193** sheets, 77 changed at 1.5×, **0 at 2× and 3×**.
    Before promoting a heuristic from a guard to a transform, count what it fires
    on and get the real list from whoever actually knows.
    **Corollary:** assert the *measurement* with a tolerance, never the *model* —
    a guard encoding one sampler's rounding fires on every future sampler change
    whether or not anything is wrong.

21. ⭐ **WHEN A CURE LANDS IN ONE PATH, NAME EVERY OTHER PATH THAT NEEDS IT —
    AND A GATE MAY NOT EXCUSE A FINDING USING A REPAIR THAT DOES NOT RUN
    THERE** (2026-08-13, #155). #148's leaf size-derived rule went into
    `UiSpike::ScaleSubtree` (runtime) in v2.94.1 and never into
    `build_dialog_static.py` — and statically-served dialogs are *deliberately*
    excluded from that sweep, so nothing repaired them. The region bubble's
    play button shipped 82px wide over an 83px art cell and tore. Worse:
    `gate_btn_undercover.py` **excused** the 1.5× residual with the words *"the
    parity class is repaired by the leaf size-derived rule"* — true in the path
    it scanned, false in the path it never scanned. **The runtime sweep and the
    static builder scale the same windows; a rule about geometry belongs to
    both.**

20. ⭐ **A BLIT HAS THREE NUMBERS — SOURCE, CROP, DESTINATION — AND SCALING ANY
    TWO OF THEM IS NOT A PARTIAL FIX, IT IS A NEW DEFECT** (2026-08-13, #154
    correction). v2.97.0 scaled the window (285→428) and the bitmap (285→429)
    and left `imagerect=(0,0,285,30)` alone, so the game sliced a 285px piece
    into a 428px window and **143px of every row stripe was bare**. The build
    printed `rects2x=0` on a file with 24 imagerects and I read past it (law
    54). Worse, **the gate passed it** — it read the window and the bitmap and
    never the crop between them. Same family as the coupled-pair law (#143);
    this names the third member. **When a gate checks a blit, make it read all
    three, and if it cannot, make it say which one it is not reading.**

19. ⭐ **A GATE THAT ONLY ASKS ABOUT YOUR OWN WORK CANNOT SEE WORK YOU NEVER
    STARTED** (2026-08-13, #154). CAM's Village Hall info screen rendered at
    1× under 1.5× fonts for the **entire life of the project**, and every gate
    stayed green — because every gate asked *"is what we built still
    correct?"*, and this dialog was never built. The builder's winner assert
    even asks the adjacent question (*"has a mod taken over one of OUR
    targets?"*) and has never asked its mirror (*"is a mod's OWN dialog scaled
    at all?"*). **Run the census in the other direction too: enumerate what
    EXISTS and subtract what is handled.** `winning_corpus.py` had been
    reporting the three CAM-only scripts as unhandled third-party holders,
    under a "What to do" heading, since the day it was written. It is now at
    **0 third-party winners** — every `.UI` in the load order is the game's or
    ours.

15. ⭐ **"THIS WASN'T LIKE THIS BEFORE" IS A BISECTION BOUNDARY, NOT AN
    OPINION** (2026-08-06, #149). Four defects were reported minutes after a
    deploy, so both of that deploy's changes were reverted. **The reverts fixed
    nothing** — the cause was a change from eight hours earlier. The user's
    sentence *"these issues weren't there when we first started on 1.5×"* was a
    better instrument than the timing coincidence.
    **When a revert does not move the symptom, the attribution was wrong. Stop
    reverting and go bisect.**

16. **A "SAFE" OVER-APPROXIMATION IS STILL A CHANGE, AND IT IS PAID FOR IN
    PIXELS** (2026-08-06, #149 — the actual cause above). `CellUnit` was widened
    to the LCM of every count that divides a sheet's width, reasoning that a
    bigger common multiple makes *any* cell divide safe. It does — and it makes
    sheets **bigger than the window drawing them**. Measured: 152 mismatches for
    the LCM set versus 34 for `{3,4}`, i.e. the "safe" choice was the worst
    option except doing nothing. **LCM-of-everything is safe against cutting and
    unsafe against fitting.**

13. ⭐ **GO FIND THE INSTANCE THAT HAS A SIBLING THAT WORKS** (2026-08-06,
    #148 — this one rule replaced ten failed theories in a day).
    *"The sun and the moon are wrong"* is consistent with a hundred mechanisms,
    so ten of them survived a full day of testing. *"**One** of these **five
    identical** buttons is wrong"* is consistent with almost none — and it named
    the cause in minutes: the broken one was the only one at an **odd left
    edge**, and `ScaleSubtree` is edge-derived, so at 1.5× an odd `l` costs the
    window exactly one pixel while the art cell keeps all 71.

    **When a defect resists, stop instrumenting the broken instance and go
    hunting for a working sibling.** The pair is the experiment; the broken one
    alone is only an anecdote. Ask the user for the case with a control in it.

14. **Build the instrument that can SEE the defect class, not another one that
    can only COUNT.** Every gate in `tools\uimap\emu\` was arithmetic — its own
    README said *"IT NEVER LOOKS AT A PIXEL"* — which is why ten theories were
    checked against numbers instead of against an image. `render_flyout.py`
    (the offline compositor) then killed two of them in three minutes each.
    Paid for twice: `MMGRID` for the minimap, this for the flyouts.

## 6. State right now

**Do not read this file for current state — a hand-maintained "state right
now" narrative rotted across v2.99.0 through v3.0.2 while still displaying as
current, correction stacked on correction. It has been removed; git history
holds it for anyone reconstructing that timeline.** Use these instead, in
order:

| Question | Read |
|---|---|
| What version is actually running? | `src\SC4UIScaleDllDirector.cpp`'s `UISCALE_VERSION_STR`, cross-checked against the running DLL's own log header — never a number written in prose here |
| What changed and when? | `VERSION-HISTORY.txt:1` (newest entry first) |
| What is open right now, and what was just tried? | `UNKNOWNS-AND-NEXT-TARGETS.md` (the open register), then `git log` — the repo root carries no session-state files by design |
| What tier / mode is the live install in? | `_tests\Set-Tier.ps1 -Status` and `_tests\Set-StockCompare.ps1 -Status` — not `Test-DatIntegrity.ps1`, which checks built artifacts, not the active tier |
| What is a known open defect? | `UNKNOWNS-AND-NEXT-TARGETS.md` §D (open defects, known mechanism) and §B (ranked unknowns) |
| What was tried and refuted? | `_tests\REGRESSION.md` — search it, do not read it front to back |

## 7. If you are a fresh instance

Read, in this order: this file → `tools\research\TRIAGE.md` →
`tools\research\METHOD.md`. Then, and only then, the subsystem doc for whatever
you are working on. `REGRESSION.md` is a reference to search, not to read
front to back.

Then run the offline gates. They take under a minute and tell you whether the
tree is in a known-good state before you change anything.
