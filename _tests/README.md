# `_tests\` — the regression net (read before running anything here)

**A script's danger is part of its API.** Every entry below states what it
touches — nothing, on-disk config, or the running game — before it states what
it proves.

Most of the net is offline: it runs without SimCity 4, exits 0 or 1, and proves
the source is intact before anyone builds it.

---

## OFFLINE — run any time, no game needed

| script | what it asserts | typical runtime |
|---|---|---|
| `Test-BootStateValidate.py` | `ScaleTier::ValidateBootState`'s truth table. A hand-edited `SC4UIScale.ini` can reach 26 incoherent combinations of `AutoScale`, `ScaleFactor`, `ScaleAll`, armed packages and screen resolution — several of them inescapable, because the UI ends up too large to navigate or the art is armed while the geometry sweep is off, and the in-game control that would fix it is gone. The gate pins which states are repaired and, just as important, which coherent ones are left alone. | seconds |
| `Test-SelectorDerive.py` | the Graphic Options selector's derivation rule: one pure function, `SelDerive(state) -> UI`, written before the C++ that mirrors it. The design it pins down — the player's scale pick is a REQUEST that is never overwritten, and the effective row is derived fresh every pass as `request if usable else Auto` — is what removes the bounce/un-bounce state machine entirely. | seconds |
| `Test-SelectorContract.py` | the same selector's SHAPE, asserted on the source, because the rule cannot defend itself from the next edit: the 250 ms tick (`SelOnTick`) polls three `GetSelection` calls and nothing else — no syscalls, no file I/O, no list mutation; `SelDerive` and `SelBuildResRows` stay pure; `RemoveAllStrings` exists in exactly one function (the diff-apply `SelPushCombo`), which is the structural end of mutating a list while the player is reading it. | seconds |
| `Test-StockTierContract.py` | stock-tier boot work is gated on the condition it actually depends on. Arming `z_SC4UIScale_SelectorUI-1x` from inside `ScaleTier::SyncStaticLayers` cannot work, because that function is not called at the stock tier; gating the static-layer sync on `spikeAutoScale \|\| tierActive` cannot work for a manual stock factor, because both are false there and the previous tier's art dats stay armed while geometry runs at 1x. | seconds |
| `Test-MutationCountInvariant.py` | in `UiSpike::ScalePanelRoot` and `UiSpike::ScaleSubtree`, every call that mutates a game window (`SetW` / `SetH` / `SetArea` / `GZWinMoveTo` / `ChildAdd` / `ChildDelete`) is paired with an increment of the scale counter. Five loops re-enumerate the whole child list because the mod's own writes can make the game destroy a later sibling; the counter is the "was anything mutated?" signal that keeps that re-verification off the 16 ms tick, and it is the same number the per-panel `%d windows scaled` lines print. | seconds |
| `Test-PackageGating.py` | every third-party package reaches a real `SyncDat` call rather than computing `depOk` and discarding it, and `SyncFont` never snapshots an already-scaled `FontStyle.ini` as the player's original — on an upgrade install the live file is the mod's own font, and preserving it as "the player's" restores a scaled font over their file at stock tier. | seconds |
| `Test-ShippingIniKeys.py` | every key documented in the shipped `SC4UIScale.ini` resolves to a real read in `src\Settings.cpp` or `src\UiSpike.cpp`, under the same section name. A documented key the DLL never reads is a promise the code does not keep, and a player has no way to tell it apart from a wrong value. Covers all four read paths: the two Win32 wide entry points, the ANSI one the live-tune poll uses, and `GetPrivateProfileFloat`, which has no trailing `W`. | seconds |
| `Test-MiniMapX8Bake.py` | the minimap terrain bake at x8. The game dispatches its per-tile blitter through a 5-entry jump table indexed by `zoom + 2` with an UNSIGNED bound (`0x7A8560 lea ecx,[edx+2]` / `cmp ecx,4` / `ja 0x7A85B0` / `jmp [ecx*4+0x7A8628]`), so zoom −3 wraps to `0xFFFFFFFF` and skips the bake, and the game alpha-blends its data cells onto black. The surrounding destination math is fully general in zoom (`destY = cellY*16 >> (zoom+4)`, tile side `256 >> (zoom+4)`), so only the dispatch stops at −2. `CodePatches::ApplyMiniMapX8Bake` rewrites those 15 bytes to index `zoom + 3` against a 6-entry table in the mod's DLL: entry 0 is the x8 blitter, entries 1..5 are the game's own stubs in their original order. | seconds |
| `Test-RegionZoomSizes.py` | at every region zoom level the source, the mask, the composite and the three run lists describe the SAME dimensions — a click mask at `[item+0x44]` still describing the stock tile while the pixels were resized under it meets a `GetPixel` with no bounds check. The shipping design re-runs the game's own `sub_7AE510` to regenerate all of them from restored pristine art, so every level is computed at an absolute factor from the pristine snapshot rather than by multiplying the current size by a ratio, which is what makes an exact round trip possible. Constants are parsed out of `src\Settings.h` so the model cannot drift from the shipping code. | seconds |
| `Test-BinaryPii.py` | byte-scans a release bundle for personal data in ASCII **and UTF-16**. Every text-based privacy check is blind to a compiled binary: without `NDEBUG`, MSVC's `assert` expands to `_wassert(..., _CRT_WIDE(__FILE__), __LINE__)`, which puts the compiler's absolute source path into `.rdata` as wide characters, where `/PDBALTPATH:%_PDB%` never reaches. This reads bytes, and reads them twice — raw, and with NUL bytes removed, the pass that turns UTF-16 back into something a byte search can find. The cure it guards is `/d1trimfile:"<repo root>\"` in both vcxproj files. | seconds |
| `Test-DatIntegrity.ps1` | every deployed dat's entry count, the 3 font sources, the DLL's presence and the Plugins-folder quarantine check, plus a DEPLOYED==BUILT content hash for every package with a canonical build output. A package left out of `Deploy-OnGameClose.ps1` rots silently — stale and fresh dats can have IDENTICAL entry counts and byte sizes, because a reference rewrite swaps equal-length hex strings, so only a content hash catches that class. **The one to run after any data change or deploy.** Update its expected counts and add a hash pair for any new package in the same commit. It FAILS between build and deploy by design: deploy, then re-run. | ~1 min |

The offline emulators and geometric gates, with their exact invocations:

- `python tools\uimap\emu\emu_subflyout.py` → `PASS - 71 checks`. Runs the
  game's own `sub_79AD00` under Unicorn, so born-at-place geometry is checked
  against the engine's arithmetic rather than a model of it.
- `python tools\uimap\emu\emu_layout.py --selftest --fresh` →
  `5 pass, 0 fail, 0 skipped`. **Use `--fresh`, not `--resume`**: with
  `--resume` the cached run reports `0 pass, 0 fail, 5 skipped`, which is a
  NULL, not a pass — it looks green at a glance and asserts nothing.
- The `gate_*.py` family under `tools\uimap\emu\` — one geometric rule each
  (offset parity, icon centring, tiled seams, 9-slice fit, strip visible rows,
  minimap snap, band docking, and the rest). Each runs offline and exits 0 or 1.

## TOUCHES ON-DISK CONFIG — reversible, but know what it changes

| script | what it changes | how to undo |
|---|---|---|
| `Set-Tier.ps1` | forces a specific scale tier for an eyes-on test, DATA AND ALL — the tier packages are renamed and the matching font is copied. Setting `AutoScale=0` with a manual `ScaleFactor` instead does NOT do this: the DLL scales window GEOMETRY and logs `layers untouched`, leaving the 2x art and the 2x font in place, so 1.5x boxes get 2x artwork — crushed panels, overlapping text, clipped boxes — which reads as a catastrophic tier bug and is the test rig. `-Windowed` / `-FullScreen -Width -Height` also stage the screen the tier is judged on, which rewrites `SC4GraphicsOptions.ini`. | `-Tier 2` or `-Auto`; `-Status` reports without changing anything |

`SC4GraphicsOptions.ini` must be written **without a BOM**. `Set-Content
-Encoding utf8` adds one, and `SC4GraphicsOptions.dll` then abandons the whole
file and boots windowed; restore it by byte-exact `Copy-Item` from a known-good
copy rather than by rewriting it.

## DANGEROUS — TOUCHES THE RUNNING GAME

### `Deploy-OnGameClose.ps1` — the standing deploy mechanism

**This is how the DLL ships. Nothing else.** The game runs **ELEVATED** and
holds `SC4UIScale.dll` and the tier dats open, so it is **never killed**: the
script polls every 5 s for the process to exit, then copies the DLL plus every
tier package and asserts the DLL size matches.

    cd _tests ; .\Deploy-OnGameClose.ps1

Run it in the background (or detached) with a window long enough for a real
play session, and **confirm the `deployed ... at HH:MM:SS` line and hash-verify
against `build\Release` before treating anything as shipped**. A watcher armed
*before* a later build ships whatever is in `build\Release` when the game
closes — check the hash, not the intent.

The script records which tier is LIVE per tier-managed family **before** any
copy runs and restores that snapshot verbatim at the end. The files on disk are
not a reliable source for that answer: reading "which tier is armed" back works
only while exactly one is armed, and on an install with two armed packages a
first-match scan picks whichever tier sorts first and disarms the correct one.
The DLL owns which tier is right — `ScaleTier` resolves the factor from the
screen when `AutoScale=1`; this script owns only whether the bytes are current.

---

## The routine verification pass

1. The offline gates: `Test-DatIntegrity.ps1` plus the `emu\` drivers for
   anything geometric.
2. Build, then `Deploy-OnGameClose.ps1`; hash-verify the deployed DLL.
3. Read the log for the acceptance line chosen **before** the build.
4. Eyes-on the specific panel at the tier under test.

## Instruments (ini-gated, in `SC4UIScale.ini`)

`[Probe] Enabled` DPROBE geometry changes · `EdgeDump` full-screen window set ·
`VisTrace` full-depth visibility and creation trace · `EdgeBlt` thin edge blits
(it sees WINDOW blits only and **cannot see the screen surface**, so a null
there leaves the screen surface unmeasured).

All ship at 0. They are re-read live only when `[UiSpike] LiveTune=1`;
otherwise they are read once at the first sweep, so editing them needs a
restart.

**Before trusting any instrument's null result, read its printf and confirm it
sits in the branch that does the thing.** A probe rooted at the wrong window,
hooked at the wrong level, armed only on state flips, installed lazily, or
reading the wrong surface returns a null that is a blind spot rather than a
measurement. See `tools\research\METHOD.md`, "YOUR OWN INSTRUMENTS CAN LIE".
