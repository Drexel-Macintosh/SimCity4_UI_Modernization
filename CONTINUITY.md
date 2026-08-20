# If you are picking this project up cold

You are holding a working reverse-engineering project against a closed-source
2003 game. Nothing here needs the original author to function. This file is
the door: current state, work in flight, and the next actions. Rewritten
2026-08-20; if that date is old, trust `VERSION-HISTORY.txt:1` and the git
log over anything below.

**What it is.** SC4UIScale is a DLL mod for **SimCity 4 Deluxe, build
1.1.641** that scales the game's interface to 1.5x / 2x / 3x for modern
high-resolution displays. See `README.md` for the product view and
`START-HERE.md` for the deep orientation (docs map, standing rules, gates).

**What state it is in.** Working and in daily use. The version is never
pinned in prose (prose rots): `UISCALE_VERSION_STR` in
`src\SC4UIScaleDllDirector.cpp` stamps the running DLL's log header, and
`VERSION-HISTORY.txt:1` is the newest ledger entry. All three tiers verified
on screen. Not yet publicly released.

---

## The five-minute orientation

| Question | Answer |
|---|---|
| Does it build? | Yes. `docs/BUILDING.md`. Visual Studio, `Release|Win32` — **32-bit, never x64**, the game is a 32-bit process. |
| Does it run? | Yes. `SC4UIScale.dll` + tier packages in `Documents\SimCity 4\Plugins`. ⚠ On the dev machine, Documents is OneDrive-redirected — the deployed files live under `C:\Users\...\OneDrive\Documents\SimCity 4\Plugins`. |
| Entry point? | `src/SC4UIScaleDllDirector.cpp` — a GZCOM director, the mod API SC4 exposes. |
| The interesting code? | `src/UiSpike.cpp` (live window-tree scaler + the in-game selector), `src/CodePatches.cpp` (byte patches in the exe's memory), `src/ScaleTier.cpp` (tier decision, package arming, boot validation). |
| The knowledge? | `research/` and `tools/research/` — the scaling laws and decompiled references. The bulk of the project's real value. |
| Deploy? | `_tests\Deploy-OnGameClose.ps1` — waits for the game to close. **The game runs ELEVATED; never kill it.** |
| Prove a deploy? | `_tests\Test-DatIntegrity.ps1` (deployed==built hashes) + the python gates in `_tests\` (each self-describes; all must exit 0). |

## Work in flight (2026-08-20): the Graphic Options selector

The active feature is an in-game settings panel injected into the game's own
Graphic Options dialog: a UI-scale selector (Auto / 1x / 1.5x / 2x / 3x),
plus Resolution and Window Mode dropdowns (Borderless / Fullscreen /
Windowed) that write `SC4GraphicsOptions.ini` + dgVoodoo's conf as a pair.
Cancel and Default Settings ship disabled, so **Accept is the only exit** and
a dialog close IS the commit. Everything applies on restart.

**Shipped and VERIFIED, v3.13.3 (deployed 11:25:36, commit `ad37a3b`;
verified on screen by the 11:31 launch — full click-through in the log,
all four pass criteria met, see the ledger entry at VERSION-HISTORY.txt:1):**

1. **The multi-second freeze is closed.** After two fix attempts shipped on
   inference, v3.13.2 shipped an in-memory instrument (PerfProbe,
   `src/Logger.h`) instead — and one launch named the stall:
   `EnumDisplaySettingsW` itself costs **3,264ms on this machine** (dgVoodoo
   sits between us and the driver), and the once-per-session enumeration ran
   on the first click. Everything the theories favoured measured innocent
   (OneDrive logger: 361 writes = 7ms; message path: 13,203 msgs = 6ms).
   Cure: a warm thread kicks the enumeration at DLL load
   (`UiSpike::WarmSelectorCaches`, called from the director constructor;
   tri-state `gSelEnumState` handshake). User confirmed: "the load is now
   only on the first load which is okay" — and with the warm thread it
   should now be zero; the SELRES log line prints its own duration.
2. **Windowed offered no resolutions** because `SelBuildResList` **had no
   Windowed branch at all** — Borderless returns early, Fullscreen has its
   block, Windowed fell through both to an empty list. Now: familiar sizes
   that fit the desktop, EXCLUDING the desktop-equal size (a desktop-sized
   window overflows once its title bar exists; that job is Borderless's).

**The instrument stays in** (cheap, in-memory): SELPERF table dumps on
dialog close and shutdown; a >500ms frame-gap watchdog and a >25ms pass
watchdog name their contributors. Read it after every launch.

## The v3.14 rewrite — SHIPPED v3.14.0 (2026-08-20, deployed, eyes-on owed)

**Executed and deployed 2026-08-20.** The ~1,400-line per-250ms
`ServiceScaleSelector` is now a state machine: `SelState` -> pure
`SelDerive` -> diff-apply, commit at close. All ten `_tests\` python gates
pass (incl. the two selector gates) and `Test-DatIntegrity` is green. The
plan below is kept as the record of what shipped; the ledger entry
(VERSION-HISTORY.txt:1) names what was stripped, kept, and the two
pre-existing red tools gates that are NOT this build's doing. **What is
owed: a user click-through** — open Graphic Options (instant), change each
combo rapidly (no stall), open each drop and hover (never empty), stage a
small res + a big scale (refused, bounces to Auto), switch mode to
Borderless (res list caps to the one desktop row), Accept, reopen (shows
"- on restart" tags), relaunch (BootState logs COHERENT).

The selector grew by accretion into a ~1,400-line per-250ms function
(`UiSpike::ServiceScaleSelector`, near `src/UiSpike.cpp:19900`) carrying six
generations of mechanism, several **measured dead but still executing**. The
approved plan (also at `~/.claude/plans/i-want-to-add-fuzzy-hopcroft.md`, and
summarized here so this repo is self-sufficient):

- **Phase 1 — strip the dead mechanisms:** the SELHIT coordinate trace (logs
  every click twice), the SELMSG bounded trace (question answered), the
  SELCAL calibration, the chained `SelectorWinProc` (only live outputs feed
  dead paths; the notice safety net's 10s timer suffices), the gfx-ini-stamp
  Accept detector (measured dead: 3 Accepts, 3 "no write ever seen" lines).
  Keep: the SELBTN button filters (identify the closing button), quieted to
  enter/click only.
- **Phase 2 — rebuild as a state machine:** one `SelState` struct (session
  facts cached, visit facts read once per open, staged picks reset per
  visit); one pure function `SelDerive(state) -> UI`; diff-apply (mutate a
  combo only when its derived rows changed; rebuild only on the tick a
  selection changed — a selection change implies every drop list is closed,
  which kills the mutate-under-open-drop class); commit at close writes only
  keys whose values changed. **Key design already pinned: the player's
  scale pick is a REQUEST never overwritten; the EFFECTIVE row derives
  fresh as `request if usable else Auto` — bounce and un-bounce need no
  state machine.**
- **Phase 3 — the spec is written and green, and the C++ mirrors it:**
  `_tests/Test-SelectorDerive.py` (23 checks: transition rows + 6 swept
  invariants) was written BEFORE the C++ as its specification.
  `_tests/Test-SelectorContract.py` is ALSO written now (source-shape gate:
  tick is a poll with no syscalls, derive is pure, RemoveAllStrings in one
  function, commit writers called only at close, rescue write pre-dialog;
  negative controls trip).
- Phase 4 (async logger) was **dropped** — the logger measured innocent.

## Open defects / next actions, in order

1. ~~**Verify v3.13.3 on screen.**~~ **DONE 2026-08-20, by the 11:31 launch
   (first launch after the deploy) — all four pass criteria met.** Warm
   thread: `SELRES display enumerated ONCE in 9201ms` landed at boot+9s,
   29s before the first dialog open; no `sel.buildResList` in any SELPERF
   bucket proves it ran off-thread. Windowed built 6 rows and committed
   1920x1200; Borderless 1 row (the desktop); Fullscreen 7 rows. SELPERF:
   no frame-gap lines, no bucket near a second; the biggest single pass is
   the 124ms commit pass (two file writes). Scale picks exercised too:
   manual 1.5x committed, then Auto. Numbers in the ledger entry. Note the
   launch ran at the STOCK tier (800x600 fullscreen); the session ended
   Borderless 2400x1600 + AutoScale=1, so the next launch derives a real
   tier — routine SELPERF read after it, as always.
2. ~~**The v3.14 rewrite**~~ **SHIPPED v3.14.0 (2026-08-20, deployed).**
   Phases 1–3 done in one build; all ten `_tests\` gates + DatIntegrity
   green. **Owed: the user click-through matrix** (in the v3.14 section
   above) and the routine SELPERF read after that launch. If it hesitates,
   the frame-gap watchdog names whether the stall is inside our brackets.
3. **Production scrub, remainder**: strikethrough sweep across research/ and
   _tests/ docs. Already done 2026-08-20: START-HERE.md's rotted version
   preamble and §6 state graveyard replaced with rot-proof pointers,
   README.md rewritten, GitHub repo description set, root strays handled
   (`probe_btn_nineslice.py` → tools/, `_seat_port.tmp` deleted).
   CHANGELOG.md if still wanted.
4. **Ledger backfill**: v3.2.4..v3.13.1 exist only as git commit messages
   (the ledger habit broke during the selector sprint; a condensed backfill
   block now sits in VERSION-HISTORY.txt below the v3.13.2 entry — expand
   any entry from `git show <hash>` if needed).
5. **Disaster Tools (closed, for the record)**: the queued "fix" for
   `0x0A41C7B2/B3` (scale the frames + stage art for the twin 62x49 disaster
   buttons) is CLOSED 2026-08-19 by user eyes-on: no visual defect at any
   tier; the `kNeverScaleIds` entry stands. Law: a static defect is a
   hypothesis until something on screen disagrees.

## Standing rules you will trip over first (full list: START-HERE.md §5)

- **Deploy only via `_tests\Deploy-OnGameClose.ps1`** — the game runs
  elevated and holds the DLL open. Never kill it.
- **Never write an ini with a BOM** (Win32 profile APIs never emit one; a
  BOM makes the game's parser miss every key — the boot validator treats an
  empty `[UiSpike]` section as a read failure, not a request for defaults).
- **Measure, don't infer.** Two freeze "fixes" shipped on inference and
  missed; one instrumented launch named the real cause. The PerfProbe
  brackets and the SELPERF/SELCLOSE/SELRES log lines exist so the next
  diagnosis starts from numbers.
- **Read the logs yourself** — `Plugins\SC4UIScale.log`, one Bash call away.
- **The 114 scaling laws** — `research/laws` / the memory file named in
  MEMORY.md. Read before touching UiSpike.cpp, CodePatches.cpp, or a `.UI`
  generator.
- **Every session ends with commit+push.** GitHub (`Drexel-Macintosh/
  sc4uiscale`, private) is the source of truth. Ledger entry and commit are
  one action.
