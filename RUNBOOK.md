# Runbook — from a bare clone to a shipped build

Assumes you have **this repository and nothing else**. No prior machine state,
no author to ask. Every step below is reproducible from a clean Windows box
plus a legally-owned copy of the game.

Read `README.md` first for what the project *is*. This file is how you
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

**One command does all of it:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\Bootstrap-Corpus.ps1
```

It builds `DbpfExtract.exe` if needed, then derives every input the builders
read but the repo cannot carry:

| It produces | Because |
|---|---|
| `tools\dbpf\extracted\<archive>\` | every DBPF the install has — **discovered, never listed** |
| `tools\dbpf\extracted-png-tgi.csv` | the PNG-store TGI list; the archive it copies is chosen by measuring PngMagic rows, not by name |
| `tools\uiscripts\extracted\` | the ~330 type-0 `.UI` layouts, renamed `.png` → `.ui` |
| `tools\dialog-static\thirdparty-src\` | the mod-owned `.UI` scripts, from **both** Plugins trees, our own packages excluded |
| `tools\dialog-static\thirdparty-art\` | the mod-owned bitmaps the builder asks for by `--emit-inputs` |

Add `-Force` to redo work already on disk, `-GameDir` / `-PluginsDir` if they
are not where it looks.

**Presence is not execution.** A cold-clone test once ran the builders from a
fresh checkout and five of nine failed — every one on a missing input, not
missing code — after an audit had verified that all the builders were
*present* and called that done. Run the bootstrap; do not assume the inputs.

The one input the bootstrap cannot always finish is the ItemIconsSub 1x source
set: 129 icons owned by other mods. Run

```powershell
python tools\itemicons\recover_sub_sources.py
```

It pulls what your Plugins tree still has and, for anything gone, inverts our
own shipped 2x package — nearest-neighbour at an integer factor is exactly
invertible, and the script *proves* that on every icon it did find before
trusting it on one it did not. On this machine 99 came from Plugins and 30 only
existed inside our own package; the control ran 99/99 exact.

If you build `DbpfExtract.exe` by hand, note that **`csc` treats a leading `/`
as an option prefix** — pass Windows backslash paths or it reports the source
file as missing.

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

**Run the whole set as a gate rather than by hand:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File _tests\Test-Builders.ps1
```

It runs all nine in dependency order and exits non-zero if any refuses. The
order is part of the test: `selective-safe` emits the refmap and the
SelectiveArt dat that `dialog-static` and `stage_icons` both read, so running
them as a flat list passes or fails for the wrong reason. Add `-Factor 1.5`
or `-Factor 3` for a tagged tier.

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

`Deploy-OnGameClose.ps1` **is the manifest — with three exceptions.** A package
that is not copied there does not ship, and the release builder parses that
same file to assemble the distribution; three packages have rotted by being
hand-placed into the Plugins folder and never wired in. If you add a package,
add it there. But `Build-Dist.ps1` cannot regex-parse ~30 of Deploy's copy
lines (named-parameter form, expression-built paths) and compensates with
hardcoded blocks — SelectorUI, CsiIcons and the ZCarbon set — so a package
added in one of those shapes must be wired in BOTH files, and the bundle's
layout-mixture tripwire is what catches a half-edit.

Preserve `SC4UIScale.log` before relaunching; it is recreated on every launch.

---

## 5. Verify before shipping

```powershell
_tests\Test-DatIntegrity.ps1                 # deployed == built
_tests\Test-ThirdPartyGates.ps1              # third-party overrides stay gated
_tests\Test-FolderDiscovery.ps1              # the DLL's discovery code, compiled + mutation-tested
_tests\Test-DistInstall.ps1                  # the public zip installer, install+uninstall round-trip
- `_tests\Test-GameFolderClean.ps1` - asserts we leave NOTHING in the
  player's SimCity 4 install folder. Run with the game CLOSED. Nothing
  else in the net looks at that folder, which is how a 23 KB leftover
  shipped for several releases while the README promised otherwise.
_tests\Sync-Check.ps1                        # repo vs GitHub; user paths + binary art BY CONTENT
python _tests\Test-PatchSiteBytes.py         # byte-patch sites still hold their expected bytes
_tests\Verify-Arming.ps1                     # after a boot: content-swap arming, STATE.txt
python _tests\Test-PackageGating.py          # SyncDat sites vs dep rows, both directions
python _tests\Test-ShippingIniKeys.py        # every seeded/reference ini key is READ by Settings.cpp
python tools\uimap\emu\gate_btn_undercover.py
python tools\upscale\gate_key_integrity.py <corpus> --factor <f>
python tools\uimap\emu\gate_patch_families_combined.py   # no two patch families collide; every site table registered
python tools\uimap\crosscheck.py                         # the offline model still reproduces the patch list
python _packaging\Test-NoDeadLinks.py --repo             # every path a tracked doc names is a path a reader can open
```

The last three matter for a documentation-only change too — the corpus cites
addresses and files, and a citation the reader cannot check is the defect.
`crosscheck.py` reads the model databases in `tools\uimap\`; regenerate those
deliberately (`census.py` then `constants.py`) when the patch list changes,
never as a side effect of running a gate.

For a sc4pac-channel release additionally run `_tests\Test-Sc4pacInstall.ps1`
(needs java + the sc4pac CLI jar + network — the most expensive gate, and the
only one that exercises the real install path).

The colour-key gate is the one to never skip. Magenta `0xFF00FF` is the game's
transparency key; if a resample nudges an exact key pixel it stops being
transparent and *draws as pink* on screen.

---

## 6. Cut a release

```powershell
_packaging\Build-Dist.ps1          # player-ready bundle
```

**There is no export step.** This working tree pushes straight to the public
remote, so what ships is decided by the `.gitignore` allowlist and proven by
`_tests\Sync-Check.ps1` — which scans the tracked set for machine paths and
refuses any file whose leading bytes are image, archive or executable,
whatever its extension. `_packaging\Build-PublicRepo.ps1` belongs to the older
two-repo arrangement and is marked superseded in its own header; do not run it
expecting its output to be what the public sees.

`_packaging\Test-NoForeignContent.py <dir>` is still worth running by hand
against a changed doc set: it refuses on names that can only mean another
project, and reports softer matches for one human read.

---

## 7. When something looks wrong on screen

In this order, because this order is what the project learned the hard way:

1. **Search `_tests/REGRESSION.md` first.** Every refuted hypothesis is
   in there with a date. A surprising share of "new" defects are already
   answered, including ones already proven *not* to be defects.
2. **Check `research/laws/feedback-sc4-scaling-laws.md`.** The numbered
   scaling laws. If your situation matches one, the answer is already
   written.
3. **Measure — do not infer, and do not judge sizes from a screenshot.** A
   screenshot reliably proves presence, colour and gross change; it does not
   measure ratios.
4. **To find what draws something, make it stop.** Suppression identifies in one
   run; "make it bigger" tests come back ambiguous.
5. **State the positive control for any null.** "The probe saw nothing" means
   nothing until you can show the probe *could* have seen it.
6. **Ledger the result the same session, including failures.**
