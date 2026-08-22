# START HERE

**SC4UIScale — runtime UI scaling for SimCity 4 Deluxe 1.1.641.**
~~Current version **v2.99.0** (DLL + data; cell-aligned sampling for state strips — see rule 22).~~
~~Current version **v3.0.1** (2026-08-16, #176 RELATCH — the SetImage crop latch is carried
across the sweep resize; see VERSION-HISTORY.txt:1).~~
Current version **v3.0.2** (2026-08-17, #182 — manual tier mode now syncs the static
layers: the gate is `(AutoScale || tierActive)`; `VERSION-HISTORY.txt:1`. Macro check
2026-08-17: `src\SC4UIScaleDllDirector.cpp:49` reads `"3.0.2"`. ⚠ the latest capture,
`_tests\captures\SC4UIScale-2026-08-17-082334.log`, still headers **v3.0.1** — the
v3.0.2 DLL rides the next `Deploy-OnGameClose.ps1` pass). Prior: v3.0.1 (#176 RELATCH,
user-confirmed); v3.0.0 — DLL + a new tool; custom third-party menu icons are enlarged
automatically at boot (#149).
*(corrected 2026-08-16 — the v2.99.0 line above was stale. `src\SC4UIScaleDllDirector.cpp:49`
reads `#define UISCALE_VERSION_STR "3.0.1"`; the v3.0.0 evidence trail below is historical:
`2026-08-15  v3.0.0  CUSTOM THIRD-PARTY MENU ICONS ARE HANDLED AUTOMATICALLY` and describes it
as "DLL + a new tool" at `VERSION-HISTORY.txt:6`; `dist\SC4UIScale-v3.0.0\` is built
(Install.ps1, Plugins\, SHA256SUMS.txt). The old descriptor — cell-aligned sampling for state
strips — belongs to v2.99.0, `VERSION-HISTORY.txt:45`, and was NOT carried forward.
`UISCALE_VERSION_STR` is what stamps the DLL's own log header
(`src\SC4UIScaleDllDirector.cpp:107`), so when this line and that macro disagree, the macro is
the one that is running — check it before trusting any version written in prose.)*
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
  ~30 byte-patched layout constants inside the executable, and render surfaces
  that must be recreated rather than resized.

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
| An in-world visual that is NOT a window (balloons, signs, glows, route dots)? | `tools\research\SC4-WORLD-OVERLAYS.md` — the renderer-side companion of SC4-UI-ENGINE.md, with the gap census of undocumented systems |
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

**Shipping:** ~~v2.99.0~~ ~~v3.0.0~~ **v3.0.1 on disk, v3.0.2 built** (see the header note —
the running DLL is whatever the last capture's header says). ~~Deployed 2026-08-14~~
**Batch deployed 2026-08-16 22:31** (#172 + #177 + #173 + the #181 key-integrity gate, one
deploy; corpus rebuilt with 5 derived lists + ladder redraw + key gate inline),
`Test-DatIntegrity` ALL PASS **with the #178 pins updated to the de-facto 261**, all
offline gates green; `gate_btn_undercover` reads **fractional residual 15x=0**. Tier
currently forced to 1.5× (`Set-Tier.ps1 -Tier 1.5`, `AutoScale=0`) — ⚠ and that manual
mode is exactly what #182 bit; its data cure (activate `-15x`, disable `-2x` for
UncoveredIcons) is queued on game close and the DLL cure is v3.0.2.

*(Version + deploy date corrected 2026-08-16. VERSION: `src\SC4UIScaleDllDirector.cpp:49`
`#define UISCALE_VERSION_STR "3.0.0"`, `VERSION-HISTORY.txt:1` "2026-08-15  v3.0.0", and the
DEPLOYED `Plugins\SC4UIScale.dll` carries the literal string "SC4UIScale v3.0.0". DATE: v3.0.0
did not exist on 2026-08-14 — the deployed DLL is stamped 2026-08-16 11:13 (matching
`build\Release\SC4UIScale.dll`) and `z_SC4UIScale_SelectiveArt-15x.dat` 2026-08-16 12:16, the
#170 rebuild. The rest of the line was re-verified the same day and left alone: `$EXPECTED` has
25 rows (`_tests\Test-DatIntegrity.ps1:13-290`) and `$BUILT_PAIRS` 29 (`:355-408`), and the
script was RUN, not assumed — it printed ALL PASS; `tools\uimap\emu\gate_btn_undercover.py`
exits 0 with the #171 fractional residual reported-not-failed; live `SC4UIScale.ini` has
`AutoScale=0` and `ScaleFactor=1.5`.)*

~~**⚠⚠ THE INSTALL IS IN STOCK MODE RIGHT NOW — RESTORE IT BEFORE TESTING.**~~
~~A 3x windowed test rig was being set up when the session ended:~~

```
# ⛔ SUPERSEDED 2026-08-16 — DO NOT RUN EITHER LINE. Kept only to show what the
# stale banner told people to do. Nothing is disabled, and the rig is at 1.5x.
_tests\Set-StockCompare.ps1 -Mode Ours      <- RUN THIS FIRST. 13 of our files
                                              are disabled; the mod is OFF.
_tests\Set-Tier.ps1 -Tier 3
```

**CORRECTED 2026-08-16 — THE INSTALL IS NOT IN STOCK MODE. THE MOD IS LIVE AT THE
1.5× TIER**, exactly as the tier line two lines above already says. Measured, not
inferred:

- `_tests\Set-StockCompare.ps1 -Status` prints `Mode : OURS (2x scaling active)`
  and `Resolution: 3840x2160 FullScreen / DirectX`. (The "2x" in that string is
  hard-coded at `Set-StockCompare.ps1:101` — it does **not** mean the tier is 2x.)
- Stock mode is the `.compare-off` suffix, **not** `.x1-disabled`
  (`Set-StockCompare.ps1:39`). There is not one `.compare-off` file in any of the
  five sites the script disables — `Documents\SimCity 4\Plugins`, that folder's
  `zzz-SC4UIScale\`, `<install>\Plugins`, `<install>`, `<install>\Apps`
  (`Set-StockCompare.ps1:45-65`) — and no `SC4UIScale.compare-state.txt`.
  `-Mode Ours` would therefore restore **0 files** and change nothing.
- `_tests\Set-Tier.ps1 -Status` prints `15x` for all seven live packages
  (SelectiveArt, DialogStatic, ItemIcons, CamUI, ItemIconsSub, SaveWarningUI,
  ThirdPartyUI), `ini: AutoScale=0 ScaleFactor=1.5`, `FontStyle.ini matches: 15x`.
  Every `-2x` and `-3x` twin carries `.x1-disabled`.
- ⚠ NamIcons and WarriorUI report `(none - dependency-gated off)` and their **15x**
  copy is `.x1-disabled` too. That is the MOD gate (NAM / Warrior not installed),
  not stock mode — do not read those two files as evidence that our layer is off.

To move tiers run `_tests\Set-Tier.ps1 -Tier <1.5|2|3>` (it renames the tier dats
AND copies the matching font; setting `ScaleFactor` in the ini by hand does not).
Confirm with `_tests\Set-Tier.ps1 -Status` + `_tests\Set-StockCompare.ps1 -Status` —
**not** `Test-DatIntegrity.ps1`, which checks entry counts and built artifacts and
never reports the active tier.

~~State as left: `SC4GraphicsOptions.ini` = **2400x1800 Windowed**;~~
~~`SC4UIScale.ini` = `AutoScale=0 ScaleFactor=3`; dgVoodoo~~
~~`FullScreenMode=false` + `CaptureMouse=false`~~ (backups: `.before-windowed-3x`,
`.before-3x-window`).

**CORRECTED 2026-08-16 — the windowed 3x rig was reverted; every value struck above
is stale.** Measured: `SC4GraphicsOptions.ini:36,41,63` = `WindowWidth=3840`,
`WindowHeight=2160`, `WindowMode=FullScreen`; `SC4UIScale.ini:111,124` =
`AutoScale=0`, `ScaleFactor=1.5`; `Apps\dgVoodoo.conf:30,41` =
`FullScreenMode = true`, `CaptureMouse = true`. The two named backup files do still
exist.

⛔ **Do not trust any state line in this file — run the two `-Status` commands
first.** This banner sat here stale across at least two deploys while contradicting
the tier line printed directly above it.

**NEXT: the 3x eyes-on round.** The border question is settled — see
`reference-sc4-windowed-mode-dgvoodoo` / the note below. What is NOT yet tested
is our layer ON at 2400x1800; that combination has never been launched.

### The windowed-mode finding (2026-08-14)

`WindowMode=Windowed` in SC4's ini **does nothing on its own** — dgVoodoo's
`Apps\dgVoodoo.conf` `FullScreenMode=true` overrides it, which is why there was
no title bar to drag. `CaptureMouse=true` compounds it by trapping the cursor
inside the client area so the title bar is unreachable. Both now `false`.

Bisected properly, one variable at a time: border present at **1024x768** stock,
then still present at **2400x1800** stock. **Resolution is innocent** — a window
taller than the desktop, and past DirectX 7's 2048 limit, still gets a border
and still drags. ⚠ That does NOT convict our layer either: `FullScreenMode` and
the layer both changed between the failing case and the working one, so the
honest state is "the wrapper setting was the fix; our layer at that size is
untested".

**Tier minimums** — ⚠ **CORRECTED 2026-08-16: the density cap is only ONE of three gates.**
`ScaleTier::Decide` returns a factor only when **all three** hold
(`src\ScaleTier.cpp:1670-1672`), on top of `PackageInstalled` (`src\ScaleTier.cpp:1666`):
`kWidestDesignPx(880) * f <= width` · `kTallestDesignPx(558) * f <= height` ·
`f <= min(w/800, h/600)` (constants `src\ScaleTier.cpp:26-27`, cap `src\ScaleTier.cpp:1659-1661`).
Combining them, the true minimums are **1.5x = 1440x1080 · 2x = 1920x1440 · 3x = 2880x2160**,
not ~~1200x900 / 1600x1200 / 2400x1800~~ — that is the density cap alone, which never binds
width, because the fit gate is stricter horizontally (880 > 800) and looser vertically (558 < 600).

On this 2400x1600 monitor 3x fails **all three** gates, not one: width 2640 > 2400,
height 1674 > 1600, cap 3 > 2.667. So ~~"height is the binding constraint — expect any 3x
breakage at the BOTTOM (the dock) first"~~ was wrong for being **exclusive**, not for naming
height: height alone drives the cap failure (`capW` = 2400/800 = 3.00 passes *exactly*;
`capH` = 1600/600 = 2.667 does not). Width binds too, and by more — the widest design piece
overhangs by **240px** against the tallest piece's **74px**. Note also that
`kTallestDesignPx` is the **Graphics Options dialog** (`src\ScaleTier.cpp:27`), not the dock,
so the dock was never what that constant measured.

3x is reachable here only by **forcing** it: `Decide` is not consulted at all unless AutoScale
is on (`src\SC4UIScaleDllDirector.cpp:127`), so with `AutoScale=0` a tier can be set below its
minimum. Under AutoScale, 3x is simply never selected at this resolution.

`Set-Tier.ps1` has no `1` option (`_tests\Set-Tier.ps1:29`, `[ValidateSet("1.5", "2", "3")]`);
1x is `Set-StockCompare.ps1 -Mode Stock`.

**⚠ SC4TouchControls is OUT of `Plugins\` right now** — moved (not deleted) to
`Documents\SimCity 4\_touch-QUARANTINE-do-not-reinstall\` at the user's request
so they could test something without it. Put it back before treating any touch
behaviour as evidence.

**#154 CLOSED v2.97.1 — USER-CONFIRMED "perfect" (2026-08-13).** CAM's three
OWN dialogs — the Village Hall / Town Hall info screen and the civic + school
query panels — are scaled for the first time. They had rendered at 1× under
scaled fonts since the project began, with every gate green, because no check
ever asked whether a *mod's own* window was scaled (rule 19).
`winning_corpus.py` now reports **0 third-party winners**: every `.UI` in the
load order is the game's or ours.

It took two builds. **v2.97.0 scaled the window and the bitmap and left the
`imagerect` crop between them at 1×** (rule 20), so every row stripe painted
285px of a 428px window — user-reported, and the gate had passed it. The
repaired rule also fixed two CAM query panels that had been drawing short
stripes since v2.38.3.

## ✅ ALL THREE TIERS ARE NOW VERIFIED ON SCREEN

~~**1.5× is closed.** Every defect reported against this tier has been fixed and
confirmed by eye.~~

⚠ **CORRECTED 2026-08-16 — 1.5× IS NOT CLOSED.** What is closed is the **#142–#153
family**, which is what the section below actually documents, and that part is
user-confirmed. Still open at 1.5× and invisible at 2×/3× by construction:

| | |
|---|---|
| **#162** | mayor's-hat and people-button hairlines in `I-c973b411`. **NOT fixed, and the mechanism is NOT known.** The even-row / `floor(oy/1.5)` duplication theory was killed by the user's press-and-hold test — do not re-quote it (`REGRESSION.md:10007`). What IS proven: the 1.5× art is a bit-exact floor-NN copy of the 1× source (0/24840, 0/20412), and these two widths already agree under BOTH the edge- and size-derived rules (90 and 81). So it is not a tiled seam and not #170's window-vs-cell defect. Every offline explanation is exhausted; the next instrument must observe the live composited surface. `REGRESSION.md:10310-10314` |
| ~~**#165**~~ | ⚠ **SUPERSEDED — #165 IS CLOSED. Do not read this row as current status.** Kept as the record of the defect as it stood on **2026-08-16**, before the fix: the 8-state sheet `{46a006b0,14416315}` shipped 204/8 = 25.5, the engine read a 25px cell, and the strip lost 4px. **CLOSED 2026-08-16 by the #171 cell-first rule, USER-CONFIRMED the same day** — see the `~~#165~~` row in the **Open** list below, which is the authoritative status, and `_tests\REGRESSION.md` § *"#171 — WIDTH AXIS CLOSED: build strips CELL-FIRST"* (line 10520 as of 2026-08-18; the user-confirmation sentence naming the 8-state radiocheck row is at :10550). ⛔ Still binding: do NOT implement HARDENING-PROPOSALS C5 — its `lcm(CellUnit, states)` cure is precisely what #157's law forbids, and its worked example is arithmetically impossible. The ORIGINAL OPEN report is `_tests\REGRESSION.md` § *"#165 OPEN, LIVE IN THE SHIPPED 1.5x PACKAGE"* (line 10065 as of 2026-08-18), superseded by the #171 block above. |
| **#171** | 132 pre-scaled buttons where the **window is right and the SHEET is wrong**, over-snapped by `ScaleDim`'s `CellUnit`. Zoom Out is 21px at 1×; `R(21*1.5) = 32`, but the 84px sheet divides by both 3 and 4, snaps on LCM 12, lands at 132 → cell **33**. Law 70's over-approximation. 0 at 2× and 3× (`ScaleDim` returns before `CellUnit` at an integer factor). The cure is an ART-dimension change, reverted and game-wide in scope — **reported, not fixed**. `REGRESSION.md:10300-10308` |

*(⚠ 2026-08-17: this three-row table is itself now partly stale — #165 closed
2026-08-16 (cell-first rule, user-confirmed), #171's width axis closed the same day and
its vertical residue shipped as #177 in the 22:31 batch (population now 0). #162 remains
open with the mechanism unknown. The Open list below carries the current state.)*

⚠ **This list is not itself an all-clear for the tier.** The Open list further down still
owes a broad 1.5× eyes-on sweep, and #123 is a 1.5× item — so read "closed" as applying to
the #142–#153 family and nothing wider. Add #162, #165 and #171 to that list, which names
none of them.

*(⚠ 2026-08-18: that has since been done — the Open list below now names all three, and its
#165 and #171 rows are struck through as closed. Status lives in the Open list, not here.)*

⚠ **A green gate is not zero defects here.** `tools\uimap\emu\gate_btn_undercover.py`
**exits 0** on #171: it prints `PASS - integer tiers exact. Fractional residual ... is the
KNOWN ScaleDim cell-snap, reported not failed` (`gate_btn_undercover.py:478-482`) and
splits its verdict by cause, so `0 BUILDER-WRONG` means the builder is clean, not that the
buttons are (`gate_btn_undercover.py:276-280`). That is law 21 in this very file.

2× and 3× were re-tested during the work and are unaffected —
2× was used deliberately as a **positive control** and came back 100% clean,
which is what proved the whole family was confined to the fractional path.

**1.5× eyes-on pass — 2026-08-06 to 08-13.** The first human look at this tier
found defects the gates could not see, because 1.5× is the only tier that can
express them. Every one is now closed and user-confirmed:

| | |
|---|---|
| #142 font rounding | FIXED — `round()` overshoots at 1.5×, must floor |
| #143 white seams | FIXED — the game's `width/3` and `width/4` cell divides stop being exact; 31%/43% of dimensions broke |
| #144 Set-Tier lied | FIXED — reported all nine packages "gated off" while all nine were loading |
| #145 fake-terrain ring | FIXED — `DOCK_NEUTRALIZE_MIN_FACTOR = 2.5` excluded 1.5× from a cure that already worked at 3× |
| #146 dashboard minimap | FIXED — `GetW() > 64` should have been `>= 64`; #89's repair never ran at 1.5× |
| **#148 reverse L** | **FIXED v2.94.1 — an ODD LEFT EDGE costs the window one pixel. The diagnosis was user-confirmed at v2.94.0; that build's two levers caused four regressions and were reverted (see below)** |
| #147 CAM graph caption | FIXED v2.94.1 — CAM binds a label LTEXT that exists nowhere; we ship the missing 20-byte resource rather than edit CAM's file |
| #149 oversized art | FIXED v2.94.2 — `CellUnit`'s LCM **overshot**: a 200px four-state sheet snapped on 8, so 300 (already a clean multiple of 4) became 304 and every cell shipped a pixel wide |
| #150 stale packages | FIXED v2.95.0 — **six of nine packages never got the #149 fix.** `gate_namicons` had been red for two hours, unread |
| #151 ratio sampler | FIXED v2.95.0 — mapping by size-ratio instead of factor **re-timed the contents** of every fractional sheet. Same dimensions, wrong pixels |
| **#152 advisor faces** | **FIXED v2.96.0 — the offset-parity law (rule 17). 14 windows seated on their frame's art aperture** |
| **#153 My Sim grid** | **FIXED v2.96.0 — same law, other axis. 21 of 22 seated; `SEATPROBE` proved the #47 hook was innocent** |

**#148 is the one worth reading — for the diagnosis AND for the two wrong
levers that shipped on top of it.**

**The diagnosis (correct).** `ScaleSubtree` is edge-derived on purpose
(~~`UiSpike.cpp:15546`~~ **`UiSpike.cpp:17111`; the rationale comment is at
`UiSpike.cpp:17207-17210` and the `newW`/`newH` computation at
`UiSpike.cpp:17278-17281`** — *line corrected 2026-08-16; 15546 is the Budget
dialog's `SetCaption` re-measure (`t->SetCaption(*cap);` at 15545), a different
function entirely*) so abutting siblings stay abutting — which makes the
scaled *width* depend on the *left edge*.
> ⚠ **Since law 86 the EXTENT is no longer purely edge-derived.** A window whose
> vtable is `0x00ADDAF0` (`stripBtnClass`, #167) takes `ScaleRound(w, f)` as a
> length instead (`UiSpike.cpp:17271-17281`), and the #148 leaf rule below
> overrides `newW`/`newH` again at `UiSpike.cpp:17314-17338`. POSITION stays
> edge-derived in the parent's design frame in both cases (#161,
> `UiSpike.cpp:17236-17239`). At 1.5×, `l=68` gives `w=71` and
`l=69` gives `w=70`, against an art cell of 71. An **odd left edge costs one
pixel**, and the uncovered right column plus bottom row draw as the reverse L.
Found because one screenshot had a **control** in it: one of five identical
Landscape buttons was wrong, and it was the only one at an odd `l`.

**Wrong lever 1 — move the button** (`parity_nudge_btn_areas`, reverted).
A nudge is up to 2px at 1.5×: invisible on the Landscape flyout (five buttons,
50px apart), obvious in the densest grid in the game. Shipped, and within
minutes: the Select-A-My-Sim face grid slid left inside its frame, the advisors
sat "left and high", the Monthly Budget rows and the bottom dock misaligned.
> **A fix that MOVES things is judged by its densest neighbourhood, not by the
> case that reported the bug.**

**Wrong lever 2 — resize the art** (`fit_state_strips_to_windows`, reverted).
`ScaleDim`'s `CellUnit` really is a guess (a 136px **four**-state sheet snaps on
`LCM(2,4,8)=8` → cell 52 where its button wants 51; it snaps *heights* too,
which a horizontal strip never needs). Rebuilding 61 sheets at
`states × window` was arithmetically right and still broke the flyout
thumbnails on hover, because **the flyout strip items are created at RUNTIME and
appear in no `.UI`** — they bind art by TGI like anything else, so the builder's
conflict check only ever compared the `.UI` consumers and reported 0 conflicts.
> **Editing geometry in a `.UI` has the scope of that `.UI`. Editing ART has the
> scope of the whole game.** Not the same blast radius, not the same evidence.

**The correct lever (v2.94.1).** In `ScaleSubtree`, a **leaf** window
(`GetChildCount() == 0`) takes its scaled size **size-derived**,
`ScaleRound(w, f)`, instead of edge-derived. Nothing moves; the size changes by
at most one pixel, so the art cell and the window agree. **Leaves only** —
containers keep edge-derived rounding, because that is what stops #143's white
seams coming back. It is a **no-op at an integer factor by construction**
(`ScaleRound(l*2)` is exact for every `l`), and it announces itself with a
`LEAFSIZE` log line, up to 8 per city.

**The lesson that generalises:** the gates passed at all three tiers the whole
time. They compare our output against our own rules; they cannot see a rule
that is wrong, and they cannot see a pixel at all. Only the third tier, a human
eye, and finally a **working sibling to compare against** found these.

### ~~✅ THE 1.5× FAMILY IS CLOSED~~ — ⚠ NARROWED: the **#142–#153** family is closed — what to keep from it

> **Corrected 2026-08-16.** This heading read "THE 1.5× FAMILY IS CLOSED", which is
> false. Three **1.5×-only** defects are open right now, and one of them is shipping:
>
> ⚠ **UPDATE 2026-08-18 — the "three open" count below is SUPERSEDED, and #165 in
> particular is CLOSED.** The 2026-08-16 correction is kept verbatim because it is the
> record of what was believed that morning. For current status read the **Open** list
> further down this file — that list, and only that list, is the status of record.
>
> * **#162** — mayor's-hat and people-button hairlines in `I-c973b411`. Mechanism found,
>   **not yet fixed**; the even-row-parity theory was killed by the user's kill test.
>   `_tests\REGRESSION.md:9809` (and `:9585`, where the report is scoped by the user's own
>   *"The lines don't exist at 2x"*).
> * ~~**#165**~~ — ⚠ **SUPERSEDED: #165 was CLOSED 2026-08-16**, the same day this
>   correction was written, by the #171 cell-first rule, and USER-CONFIRMED that day.
>   Ledger: `_tests\REGRESSION.md` § *"#171 — WIDTH AXIS CLOSED: build strips
>   CELL-FIRST"*, line 10520 as of 2026-08-18 — the sentence naming the 8-state
>   radiocheck row is at `:10550`. Status of record is the `~~#165~~` row in the **Open**
>   list further down, not this bullet.
>   The original report, kept for the record: the 8-state `{46a006b0,14416315}` strip lost
>   4px because `204/8 = 25.5` is fractional where 2× and 3× are integer, and it was
>   LIVE in the shipped `z_SC4UIScale_SelectiveArt-15x.dat` at the time —
>   `_tests\REGRESSION.md` § *"#165 OPEN, LIVE IN THE SHIPPED 1.5x PACKAGE"*, line
>   10065 as of 2026-08-18.
>   (⛔ the HARDENING-PROPOSALS C5 cure is wrong — do not implement it. That still stands.)
> * **#171** — 132 pre-scaled buttons whose ART cell is over-snapped by `ScaleDim`'s
>   `CellUnit`; **0 at 2× and 3×**. `_tests\REGRESSION.md:10300`.
>
> What *is* closed is the **#142–#153** eyes-on family tabled above (2026-08-06 to 08-13).
> The four causes and the lessons below are from that family, and they still stand.

**2× was used as a positive control and came back 100% clean**, which is what
proved every remaining defect lived strictly in the fractional-factor path.
That single test was worth more than any instrument built that week.

The four causes, all measured, none guessed:

| # | cause | shape |
|---|---|---|
| #149 | `CellUnit`'s LCM **overshot** | a "safe" over-approximation is paid for in pixels |
| #150 | **six of nine packages never rebuilt** | a fix is not shipped until every consumer carries it |
| #151 | the sampler mapped by **ratio, not factor** | a guard for a hazard never measured is an unintended change |
| #152/#153 | **odd offsets die at f=1.5** | the offset-parity law, rule 17 |

**The instrument that ended it:** `SEATPROBE` in `BmpCtxBltThunk` printed the
destination **origin** beside the window's own L,T — two numbers the existing
`BMPX` line never had. `dst origin=(0,0)` on every draw proved the #47 hook
blits in window-local space and contributes nothing to placement. One launch.

**Two failures were self-inflicted and are the most useful entries in
`REGRESSION.md`:** a red gate that went unread for two hours (#150), and a
correct fix reverted because a machine-generated regex turned `` into a
backspace byte and produced a *true* error message with a *false* implication
(#153, rule 18).

**Open, in rough priority order:**

| | |
|---|---|
| ~~#165~~ | ✅ **CLOSED 2026-08-16 by the #171 cell-first rule — USER-CONFIRMED 2026-08-16. THIS ROW IS THE STATUS OF RECORD FOR #165;** the two earlier "OPEN AND LIVE" passages higher up this file are dated 2026-08-16 as well but were written before the fix landed, and are marked superseded there. `{46a006b0,14416315}` now ships `8 × R(17×1.5) = 208`, cell 26 exactly, instead of 204/8 = 25.5. No `kCellCounts` change was needed — sizing the sheet from its CELL makes the state count irrelevant. **Re-verified by MEASUREMENT 2026-08-18** (the shipped width had never been re-read): `tools\selective-safe\stage-15x\T-0x856ddbac_G-0x46a006b0_I-0x14416315.png` is **208×26, cell 26.000 exact**; the integer controls are unchanged at 1× 136×17, 2× 272×34, 3× 408×51. Ledger: `_tests\REGRESSION.md` § *"#171 — WIDTH AXIS CLOSED: build strips CELL-FIRST"* (line 10520 as of 2026-08-18; the user-confirmation sentence naming the 8-state radiocheck row is at :10550). The OPEN report it supersedes is `_tests\REGRESSION.md` § *"#165 OPEN, LIVE IN THE SHIPPED 1.5x PACKAGE"* (line 10065 as of 2026-08-18) — that heading still reads "OPEN" and must not be quoted as current. |
| ~~#171~~ | **WIDTH AXIS CLOSED 2026-08-16.** `ScaleDim` now sizes a `cell-strips.txt` sheet as `states × R(cell1x, f)` and skips `CellUnit`. Art-snapped 132 → 84, runtime residual 34 → 28, and 2206/2206 entry payloads byte-identical at 2× and 3× (control proven by hash). ⚠ This is **not** the reverted `fit_state_strips_to_windows` — it never consults a window, only the sheet and its state count. `_tests\REGRESSION.md:10449` |
| ~~**#177**~~ | **SHIPPED in the 2026-08-16 22:31 batch (eyes-on owed).** The cure is the existing `--height-exact-strips` flag fed a **DERIVED subset** (`find_cell_strips.py` emits `height-exact-strips.txt`: 194 strips → 150 exact, 44 keep the snap with named reasons); 21 sheet heights changed, every one toward `R(h*f)`, 0 at 2×/3×. The old revert is EXPLAINED, not overridden — the real hazard was a rule-(b) consumer in `c973b411`, excluded by construction; the historical note blamed the wrong sheet (`14415860`, a provable no-op). `gate_btn_undercover` now reads **fractional residual 15x=0** — the #171/#177 art-cell population is EMPTY. `_tests\REGRESSION.md:10749` |
| ~~**#176**~~ | **CLOSED v3.0.1, USER-CONFIRMED 2026-08-16 21:04 ("extends all the way").** Root cause was neither widget's art: the HUD groove's `imagerect` is a **SetImage bind-time LATCH** that raced our sweep (⭐ the LATCH LAW), healed only by a sim rating tick — the tier split was never real. Cure = RELATCH at the resize site, latch-signature keyed, armed per root. The six polls bars are `cSC4WinTrendBar` and **immune** (every geometric input read live per frame; their real residue was the six-cell fill strip, now in `find_cell_strips.py`'s CODE_BOUND). `tools\research\SC4-UI-ENGINE.md` §2.6; `_tests\REGRESSION.md:10650` |
| ~~#172~~ | **SHIPPED in the 22:31 batch (eyes-on owed).** User decision: clamp the query pair's art to its window, scoped to the two TGIs; all six sheets land exactly `R(36f) x R(21f)`; the 800x600 twin harmonized. `_tests\REGRESSION.md:10907` |
| ~~#173~~ | **SHIPPED (UncoveredIcons via the existing builder) — then its 1.5× regression exposed #182.** The package landed 2x-active by deploy pattern and manual mode never synced it, so the 2x strip served at 1.5× (icon shifted right, wrong hover — user-reported). Data cure queued on game close; DLL cure = v3.0.2. `_tests\REGRESSION.md:10773` and `:11000` |
| **#178** | **Decision still owed: DialogStatic 261 vs 262.** The single differing entry is the CAM intro splash `{856ddbac,46a006b0,ea7f0eae}` — 261 keeps it only in the dependency-gated CamUI package, 262 also ships CAM-derived art to users without CAM. Pins are at the de-facto **261** since the 22:31 batch; 2x/3x are 262. Ties to the pre-release third-party content audit. `_tests\REGRESSION.md:10575` |
| **#182** | **DLL half fixed in v3.0.2 (deploy pending), data half queued.** Manual tier mode never ran `SyncStaticLayers` — a gate on HOW the factor was chosen instead of WHAT it is, the #149 scan's lesson bitten a second time. Verify after next boot: `ScaleTier` lines present under `AutoScale=0`, UncoveredIcons `-15x` active, `UNCOVERED=0` scan line. `_tests\REGRESSION.md:11000`; `VERSION-HISTORY.txt:1` |
| **#162** | mayor's-hat + people-button hairlines in `I-c973b411`, **not fixed and the MECHANISM IS NOT KNOWN**. ⛔ Two verdicts in `REGRESSION.md` are superseded and must not be quoted: `:9684` "CLOSED (pending eyes-on)" and `:9835` "MECHANISM FOUND". The `floor(o/1.5)` even-row parity theory was **KILL-TESTED AND REFUTED** (`:10033`) — the user held the button down and the line stayed. Geometry is exact and the art is a byte-exact NN copy, so it is not a tiled seam either. Every offline avenue is exhausted; the next instrument must observe the LIVE composited surface (`PROBES-NEEDED.md` L-A2). |
| 1.5× eyes-on | broad sweep still owed — other panels are not confirmed |
| #138 intro video | four geometry sites patched and verified applied, no visual change. Something downstream also decides the rect |
| #104/#105/#107 | shutdown spin — the WinMgr valid set is wholesale empty before teardown; probe built, awaiting a capture |
| #97 | two-knob scaling: UI size and text size independently |
| #123/#124/#125 | 1.5× ring seat, DVMAP snap consolidation, Data Views fill at 768 |
| #141 | first city open costs 54 s with a large plugin set. Measured, no lever found. One measurement outstanding: the user-vs-kernel CPU split, which `Trace-CityOpen.ps1` now records automatically |
| publish | curated public tree builds clean; nothing is on GitHub |

*(Three rows added 2026-08-16: this list had gone a day stale and carried none of
the 1.5×-only defects opened on 2026-08-15/16, including one shipping live. Not
claimed to be exhaustive — check `REGRESSION.md` from #162 onward before trusting
it, and note that the "✅ THE 1.5× FAMILY IS CLOSED" heading above this list was
itself stale for the same reason and is corrected in the same pass.)*

*(Refreshed 2026-08-17 after the #176→#182 session: #176/#177 struck closed/shipped,
#172/#173/#178/#182 rows added. Struck, not deleted, per house rule. Eyes-on still
owed from the 22:31 batch: the #172 query pair, the #177 spots, the #173
`UNCOVERED=0` boot line, and a post-batch #162 ThinBlt capture — ⚠ preserve the log
BEFORE any relaunch; see `_tests\LESSONS-2026-08-16.md` §5.)*

**Known dead — do not retry** (all measured, details in `REGRESSION.md`):
region rotation (tiles are baked at save time); any message-queue trick to run
earlier during city load (the game does not pump messages then); resizing a
render surface in place; growing a game-owned buffer from our own tick.

## 7. If you are a fresh instance

Read, in this order: this file → `tools\research\TRIAGE.md` →
`tools\research\METHOD.md`. Then, and only then, the subsystem doc for whatever
you are working on. `REGRESSION.md` is a reference to search, not to read
front to back.

Then run the offline gates. They take under a minute and tell you whether the
tree is in a known-good state before you change anything.
