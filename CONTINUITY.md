# If you are picking this project up cold

You are holding a working reverse-engineering project against a closed-source
2003 game. Nothing here needs the original author to function. This file is the
door; read it before anything else.

**What it is.** SC4UIScale is a DLL mod for **SimCity 4 Deluxe, build 1.1.641**
that scales the game's interface to 1.5x / 2x / 3x so it is usable on modern
high-resolution displays. The game has no UI scaling of its own and its
interface is hard-coded at roughly 1024x768 assumptions.

**What state it is in.** Working and in daily use. Version 3.0.38. Confirmed on
screen at 1.5x (2400x1600) and 3x (3840x2160). It is not yet publicly released.

---

## 1. The five-minute orientation

| Question | Answer |
|---|---|
| Does it build? | Yes. `docs/BUILDING.md`. Visual Studio, Win32/x86 — **32-bit, never x64**, the game is a 32-bit process. |
| Does it run? | Yes. Drop `SC4UIScale.dll` + the tier art packages into `Documents\SimCity 4\Plugins`. |
| What's the entry point? | `src/SC4UIScaleDllDirector.cpp` — a GZCOM director, the mod API SC4 exposes. |
| Where's the interesting code? | `src/UiSpike.cpp` (walks and rescales the live window tree) and `src/CodePatches.cpp` (patches constants inside the game's own executable). |
| Where's the knowledge? | `research/` — see §3. This is the bulk of the project's real value. |

---

## 2. Six things that will cost you a day each if nobody tells you

These are not style preferences. Each one was learned by losing time to it.

1. **The game runs ELEVATED and holds its files open.** You cannot overwrite
   the DLL or the art archives while it is running, and you must never kill the
   process — it can half-write a save. Deploy by waiting for a clean exit.

2. **Magenta `0xFF00FF` is the game's transparency key.** Any interpolating
   resample turns an exact key pixel into `0xFE01FE`, the key test then misses
   it, and the colour *draws* as pink. Nearest-neighbour is the default at every
   scale factor for this reason, and it is not negotiable without a key-aware
   path.

3. **Never write a game `.ini` with a BOM.** The parser silently fails.

4. **A constant sweep over `.rdata` is blind to inline immediates.** Several
   values that control on-screen geometry are `imm32` fields *inside
   instructions*, not data. A "the constant is inert" conclusion is worthless
   unless inline immediates were scanned too. This cost seventeen test launches
   on one defect.

5. **Integer scale factors are exact; 1.5x is not.** At 2x and 3x one source
   pixel maps to a clean N×N block. At 1.5x you must distribute one extra pixel
   per two, which no arrangement makes even. A whole class of defects exists
   only at 1.5x — see the `#171`–`#178` section of the ledger.

6. **Suppression identifies; scaling does not.** To find out what draws
   something, make it *stop*, not grow. A "make it bigger" test that shows no
   change is ambiguous three ways; a "make it vanish" test answers in one run.

---

## 3. Where the knowledge lives

`research/` is not incidental — it is the accumulated model of an undocumented
engine, and it is worth more than the source code.

| Path | What it holds |
|---|---|
| `research/laws/` | **Read `feedback-sc4-scaling-laws.md` first.** 105 numbered laws, each earned from a specific failure, each stating what went wrong and what to do instead. If you read one file in this repo, read that one. |
| `research/tools/research/` | Per-subsystem engine references — the window engine, the region screen, item icons, fonts and dialogs, in-world overlays, the city situation indicators. |
| `research/_tests/REGRESSION.md` | The ledger. Every fix and, more importantly, **every refuted hypothesis**, dated. When something looks wrong, search here before forming a theory — a surprising amount is already answered. |
| `research/START-HERE.md` | The original working entry point, with current defect status. |
| `research/tools/uimap/` | An offline model of the UI layout, used to test changes without launching the game. |

---

## 4. How the work is actually done

The method matters as much as the findings, because the game gives you almost
nothing for free.

- **Measure, never infer.** Values that were measured landed first try; values
  that were reasoned about cost two or three attempts. This is written down
  because it kept being true.
- **State the positive control for every null.** "The probe found nothing" is
  not evidence until you can show the probe *could* have seen the thing. Several
  multi-day dead ends were filtered nulls that looked like facts.
- **A screenshot proves presence and colour, not ratios.** If an answer depends
  on relative size, change one element by a large factor and see which moved.
- **Exaggerate the probe.** When two overlapping elements are similar in size,
  a 1.5x change cannot separate them; a 3x change answers immediately. Dial back
  after you know.
- **Ledger the result the same session**, including the failures. The refutations
  in `REGRESSION.md` have saved more time than the fixes.

---

## 5. What is open

Read `research/_tests/REGRESSION.md` for the live list. As of this import the
notable ones are:

- **1.5x visual quality.** Softer than 2x/3x for the arithmetic reason in §2.5.
  A ×3-then-÷2 supersampling path was prototyped (upscale ×3 with nearest, which
  is exact and key-safe, then downsample 2:1) but is **not shipped or verified**.
- **A shared-path risk in the offer-balloon patch.** The indicator's backing quad
  is not category-guarded, so scaling it may also resize other dispatch markers.
  Untested — no emergency marker has been observed at a scaled tier.
- **Documentation contradictions.** Several research documents carry superseded
  claims alongside their corrections. The corrections are right; where two
  passages disagree, the later dated one wins.

---

## 6. Provenance and licence

Our code is public domain (CC0 1.0) — see `LICENSE`. Vendored dependencies keep
their own licences: `gzcom-dll` is LGPL-2.1 and MinHook is BSD-2, both recorded
in `THIRD-PARTY-NOTICES.md`.

No game assets are redistributed. The art packages are generated at build time
from the player's own installed game files, which is why the build tooling needs
a real SimCity 4 installation present.

---

## 7. Where to go next

`RUNBOOK.md` is how you operate this. Read it in order; §1 is not optional and
nothing art-related works until it is done.

The first two commands on a machine that has never built this:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\Bootstrap-Corpus.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File _tests\Test-Builders.ps1
```

The first derives every input the repo deliberately does not carry. The second
proves all nine package builders actually run, which is the only check that
distinguishes a repo that *contains* the project from one that can *continue*
it — on 2026-08-18 an audit confirmed the first and a cold-clone test found
five of the nine could not run at all.
