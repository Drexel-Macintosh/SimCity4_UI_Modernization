# Runbook — from a bare clone to a shipped build

Assumes you have **this repository and nothing else**. No prior machine state,
no author to ask. Every step below is reproducible from a clean Windows box
plus a legally-owned copy of the game.

Read `CONTINUITY.md` first for what the project *is*. This file is how you
*operate* it.

---

## 0. What you must install

| Need | Why | Note |
|---|---|---|
| **SimCity 4 Deluxe, build 1.1.641** | The mod patches this exact build. | Other builds will refuse to patch — the version check is deliberate, not a bug. |
| **Visual Studio** with C++ desktop workload | Builds the DLL. | **Win32 / x86 only.** The game is a 32-bit process; an x64 build cannot load. |
| **.NET SDK** | The DBPF and upscaler tools are C#. | `tools/dbpf`, `tools/upscale`. |
| **Python 3** + `pillow` | Art pipeline and most analysis tools. | `pip install pillow` |
| **Python `capstone`** | Only for disassembly work. | `pip install capstone` — optional unless you are reverse-engineering. |
| **PowerShell** | Deploy, tier switching, gates. | Windows PowerShell 5.1 is fine. |

Set `SC4_GAME_DIR` if the game is not at the default Steam path. Several
scripts fall back to it.

---

## 1. Regenerate the 1x art corpus — **you must do this first**

**No game art is redistributed in this repository, deliberately.** The art
packages are built from *your own* installed game files. A fresh clone has the
build recipe but not the inputs, so nothing art-related will work until you
extract them.

```powershell
# Extract every DBPF archive the game ships.
# ⛔ The count is DISCOVERED, not listed - SC4 ships NINE archives and a
# hand-written inventory has silently missed one before.
tools\dbpf\DbpfExtract.exe "<game>\SimCity_1.dat" tools\dbpf\extracted\SimCity_1
# ...repeat for every .dat found under the install
```

Then rebuild the scaled corpus for the tiers you want:

```powershell
tools\upscale\Rebuild-Corpus.ps1 -Factor 1.5,2,3
```

This also regenerates the **derived lists** (`cell-strips.txt`, `no-smooth.txt`,
`height-exact-*.txt`, `nine-slice.txt`). Those lists are *derivations, never
hand-maintained inventories* — a hand list rots silently and the project has
been burned by exactly that. If a script demands a list and it is missing or
empty, it throws rather than proceeding, and that is intentional.

---

## 2. Build the DLL

See `docs/BUILDING.md`. Release / Win32.

Output: `build/Release/SC4UIScale.dll`.

---

## 3. Build the art packages

`tools/packages/PACKAGES.md` is the per-package recipe. The main one:

```powershell
python tools\selective-safe\build_selective_safe.py --factor 1.5   # -> tools\packages\15x\
python tools\selective-safe\build_selective_safe.py --factor 2     # -> the 2x artifacts
python tools\selective-safe\build_selective_safe.py --factor 3     # -> tools\packages\3x\
```

Integer tiers are the control: a rebuild at 2x or 3x must produce **byte-identical
entry payloads** to what shipped. Compare payloads per TGI, never the file hash —
a DBPF header carries a timestamp that changes on every single build.

---

## 4. Deploy and test

**The game runs elevated and holds the DLL and archives open.** Never kill it;
that risks a half-written save. Wait for a clean exit, then deploy.

```powershell
_tests\Deploy-OnGameClose.ps1          # waits for exit, then copies everything
_tests\Set-Tier.ps1 -Tier 1.5          # force a tier, art and font included
_tests\Set-Tier.ps1 -Tier 1            # 1x baseline control - all packages off
_tests\Set-Tier.ps1 -Status            # report only
```

`Deploy-OnGameClose.ps1` **is the manifest.** A package that is not copied there
does not ship, and the release builder parses that same file to assemble the
distribution. Three packages have rotted by being hand-placed into the Plugins
folder and never wired in — they looked fine locally and were simply absent on
a clean install. If you add a package, add it there.

Preserve `SC4UIScale.log` before relaunching; it is recreated on every launch.

---

## 5. Verify before shipping

```powershell
_tests\Test-DatIntegrity.ps1                 # deployed == built
_tests\Test-ThirdPartyGates.ps1              # third-party overrides stay gated
python tools\uimap\emu\gate_btn_undercover.py
python tools\upscale\gate_key_integrity.py <corpus> --factor <f>
```

The colour-key gate is the one to never skip. Magenta `0xFF00FF` is the game's
transparency key; if a resample nudges an exact key pixel it stops being
transparent and *draws as pink* on screen.

---

## 6. Cut a release

```powershell
_packaging\Build-Dist.ps1          # player-ready bundle
_packaging\Build-PublicRepo.ps1    # public source export, privacy-gated
```

`Build-PublicRepo.ps1` runs `Test-NoForeignContent.py`, which refuses to export
if it finds user paths, hostnames, other-project names, or tokens. That gate is
why this repository is clean; keep it in the path.

---

## 7. When something looks wrong on screen

In this order, because this order is what the project learned the hard way:

1. **Search `research/_tests/REGRESSION.md` first.** Every refuted hypothesis is
   in there with a date. A surprising share of "new" defects are already
   answered, including ones already proven *not* to be defects.
2. **Check `research/laws/feedback-sc4-scaling-laws.md`.** 105 numbered laws.
   If your situation matches one, the answer is already written.
3. **Measure — do not infer, and do not judge sizes from a screenshot.** A
   screenshot reliably proves presence, colour and gross change; it does not
   measure ratios.
4. **To find what draws something, make it stop.** Suppression identifies in one
   run; "make it bigger" tests come back ambiguous.
5. **State the positive control for any null.** "The probe saw nothing" means
   nothing until you can show the probe *could* have seen it.
6. **Ledger the result the same session, including failures.**
