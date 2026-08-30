# START HERE

**SC4UIScale — runtime UI scaling for SimCity 4 Deluxe 1.1.641.**

Contributor orientation: the document map, the standing engineering rules,
and how to build, test and deploy. For the product view read
[README.md](README.md) first; this file is for working on the code.

**The current version is never pinned in prose — prose rots.** Two sources
cannot rot: `UISCALE_VERSION_STR` in `src\SC4UIScaleDllDirector.cpp` is the
version that stamps the running DLL's log header, and `VERSION-HISTORY.txt:1`
is the newest ledger entry. When any document disagrees with the macro, the
macro is the one that is running.

---

## 1. What this is

SimCity 4's interface is hard-coded for 1024×768. This project renders the UI
at 1.5×, 2× or 3× on a high-DPI screen while the world keeps rendering at
native resolution. Two halves that must agree:

- **Data** — enlarged copies of the game's UI art and `.UI` layout scripts,
  shipped as DBPF packages that load after the originals and win.
- **Runtime** — `SC4UIScale.dll`, a gzcom-dll plugin: live window geometry,
  byte-patched layout constants inside the executable, and render surfaces
  that must be recreated rather than resized.

Nothing modifies a game file. Everything is in-memory, per session.

## 2. Where things are

| Read | When |
|---|---|
| [README.md](README.md) | The product: what it is, tiers, requirements, install |
| [docs/](docs/) | How it works, what it scales, the package manifest, compatibility, building |
| [research/laws/](research/laws/) | **Lessons learned** — the scaling laws, each paid for by a real defect. Start at the [index](research/laws/README.md) |
| [tools/research/](tools/research/) | **The SDK reference** — SC4's UI engine documented from measurement: `SC4-UI-ENGINE.md` first, `TRIAGE.md` for any new defect, `METHOD.md` for how work happens here |
| [tools/uimap/](tools/uimap/) | **The offline simulator** — layout emulation, gates and compositors that adjudicate fixes without launching the game |
| [_tests/](_tests/) | **The gates** — deploy, integrity and offline verification; the suite reference is `_tests\README.md` |
| [RUNBOOK.md](RUNBOOK.md) | From a bare clone to a shipped build: corpus bootstrap, package builds, release cuts |
| `_packaging/` | Public-release build + the checks that gate it |
| [CHANGELOG.md](CHANGELOG.md) · [VERSION-HISTORY.txt](VERSION-HISTORY.txt) | Release history · the full engineering ledger |
| [research/KNOWN-LIMITATIONS.md](research/KNOWN-LIMITATIONS.md) | Known limitations — the single status list |

Generated files (`REPORT*.md`, `BUILDER-CENSUS.md`, `CONSTANT-MAP.md`,
`coverage-matrix.md`, `package-list*.txt`) are pipeline **output**. Re-run the
generator; do not hand-edit them, and do not treat them as sources of truth.

## 3. Standing rules — timeless, each paid for

1. **The game runs ELEVATED. Never kill it.** It holds the DLL and the dats
   open. Deploy with `_tests\Deploy-OnGameClose.ps1`, which waits for a clean
   exit.
2. **Measure, don't infer.** Every measured value landed first try; every
   screenshot-inferred one cost builds. Build the instrument, read it, then
   act. A screenshot proves presence and colour, never ratios.
3. **A null is not evidence.** State the positive control — show the
   instrument *could* have seen the thing — before believing it saw nothing.
   Two blind instruments agreeing are worth exactly as much as one.
4. **Gates before deploy.** Run the offline gate suite before theorising and
   before shipping; a red gate that goes unread is worse than no gate.
   Integer tiers (2×, 3×) are the control for any fractional-tier metric: a
   new metric that is nonzero at an integer factor is measuring itself.
5. **Never write an ini with a BOM.** The game's config parsers abandon
   UTF-8-BOM files; copy config files byte-exact, never through a re-encoding
   cmdlet.
6. **GitHub is the source of truth.** Every session ends with a ledger entry
   in `VERSION-HISTORY.txt` plus commit and push, as one action.
7. **Never modify game files or another mod's files.** We ship overrides that
   load later, gated on the mod being present.
8. **SC4's plugin scan is RECURSIVE.** A stash folder inside `Plugins\`
   disables nothing. Only an extension rename or a move OUT of the tree does.
9. **Coverage means OUR FILE LOADS LAST for that resource** — not "the
   resource is in one of our packages". Root files load before subfolders;
   overriding another mod requires a folder that sorts after it
   (`zzz-SC4UIScale\`).
10. **A package is not finished until it is in `Deploy-OnGameClose.ps1` AND
    `Test-DatIntegrity.ps1`.** Packages have rotted from exactly this
    omission while every gate stayed green.
11. **The docs are the SDK.** Consult in order: our docs → the SDK headers in
    `vendor\gzcom-dll\` → the live instruments → the disassembler → a shipped
    experiment. An answer already in this repo is not allowed to be
    rediscovered by experiment.
12. **Law (northstar): two questions on every diagnosis, never one** —
    *(a) have we hit this before?* and *(b) is the way we fixed it then
    viable here?* If it is, port that fix; do not design a new mechanism
    beside it. If it is not, say why in one sentence before writing anything.
13. **Law (control): go find the instance that has a sibling that works.**
    One broken of five identical controls names a cause; the broken one alone
    is an anecdote. The pair is the experiment.
14. **Law (parity): when one tier misbehaves and a sibling is confirmed
    fixed, the default hypothesis is "the known cure never reached this
    one".** Check the gate that decides who gets the fix — a factor
    threshold, a mod gate, an id list.
15. **A fix that must re-apply every tick is a fight, not a fix.** Find the
    game's own path and be correct at birth.

The full numbered law collection lives in
[research/laws/](research/laws/README.md); the scenario matrix every fix must
be tested across is [_tests/SCENARIOS.md](_tests/SCENARIOS.md).

## 4. Build, test, deploy

```
:: build (Win32 only — the game is a 32-bit process)
msbuild src\SC4UIScale.vcxproj -p:Configuration=Release -p:Platform=Win32

:: deploy (waits for the game to close — NEVER kill it, it runs elevated)
_tests\Deploy-OnGameClose.ps1

:: prove the install matches what was built
_tests\Test-DatIntegrity.ps1
_tests\Test-ThirdPartyGates.ps1

:: offline gates — no game needed, all must exit 0
python tools\uimap\emu\gate_namicons.py
python tools\uimap\emu\gate_patch_families_combined.py
python tools\uimap\emu\gate_advice_rowx.py
python tools\uimap\emu\gate_ordinance_namex.py
python tools\uimap\emu\gate_103_twin_ids.py
python tools\uimap\emu\gate_graphs_banddock.py
python tools\flyout-sim\gate_subnative.py
```

From a cold clone, run `tools\Bootstrap-Corpus.ps1` before any package build:
no game art is redistributed in this repository, so the builders' inputs are
derived from your own installation (full procedure in
[RUNBOOK.md](RUNBOOK.md)). Rebuild all three tiers together
(`--factor 1.5`, `--factor 2`, `--factor 3`) or the suite fails on mismatched
counts — and 1.5× is where rounding bugs hide, because 2× hides them.

If the exe-pinned gates fail with `fingerprint mismatch`, the game was
reinstalled or re-patched. **Do not just re-pin.** Read
`_tests\REGRESSION.md` → "THE 4GB PATCH SILENTLY BLINDED EVERY EXE-PINNED
GATE" for the procedure: bypass, run the byte assertions, re-pin only if they
all pass, and write down that you did.

## 5. If you are a fresh instance

Read, in this order: this file → `tools\research\TRIAGE.md` →
`tools\research\METHOD.md`. Then, and only then, the subsystem doc for
whatever you are working on. `_tests\REGRESSION.md` is a reference to search,
not to read front to back.

Then run the offline gates. They take under a minute and tell you whether the
tree is in a known-good state before you change anything.
