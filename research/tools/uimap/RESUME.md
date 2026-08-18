# RESUME - tools\uimap (offline UI model, STAGE 1+2)

Everything in this folder is **offline and read-only with respect to the
game**. The exe is opened `rb`; no game file, no `src\*.cpp`, no `dist\`
file is ever written. Nothing durable lives in the scratchpad.

## The one command

```
cd "<repo root>\tools\uimap"
python scan_text.py     --resume
python build_funcs.py   --resume
python census.py        --resume --discover
python constants.py     --resume --factor 2.0
python crosscheck.py
python gen_codepatches.py --factor 2.0 --out generated-sites-2x.txt
python gen_codepatches.py --factor 2.0 --only-new --out generated-NEW-sites-2x.txt
```

Run them in that order. Each one is **idempotent**: running without
`--resume` simply redoes the work and produces the same files. `--resume`
skips units already marked `done` in `state.json`.

## What state.json means

```json
{ "units": { "<stage>/<unit>": { "status": "done", "ts": "...", ... } } }
```

`status` is `pending | done | failed`. A unit is written to disk
**immediately after it finishes**, by atomic replace - so an interruption
loses at most one unit, never the whole run.

| stage | units | one unit = | partials land in |
|---|---|---|---|
| `scan` | `000` .. `103` | 64 KB of `.text` | `_work\calls\NNN.json` |
| `funcs` | `agg`, `vtab`, `build` | one whole pass | `_work\edges.json`, `_work\vtab.json`, `funcs.json` |
| `census` | `prim_<VA>` per primitive, `vtgeom`, `ident`, `discover`, `assemble`, `md` | one primitive's whole call-site set | `_work\census\*.json` |
| `constants` | `b_<builderVA>` per builder, `assemble`, `md` | one builder function | `_work\constants\*.json` |
| `crosscheck` | `run` | the whole compare | `_work\crosscheck.json` |

To redo one stage from scratch without touching the others:

```
python -c "import common as C; C.State().reset_stage('constants')"
python constants.py --resume
```

`_work\` is a rebuildable cache. Deleting it is always safe; the next
`--resume` run notices the missing partials and redoes those units.

## What "done" looks like

```
scan_text     104 shards, state {'done': 104}
build_funcs   edges: 114521 -> 15176 call-target starts + 16937 vtable-only
              funcs.json: 32113 functions
census        192 primitive call sites in 12 owner functions
              0 incomplete, 0 validation problems
constants     292 geometry constant sites, 55 twin groups
crosscheck    MISSES 0
```

The two acceptance gates:

1. **`census.py` must report 0 incomplete and 0 validation problems.**
   Validation is independent of any hand table: the text factories end
   with a font-style GUID and an R/G/B triple, so a push-run walk that
   drifted by one stops looking like one.
2. **`crosscheck.py` must report `MISSES: 0`.** A miss means
   `CodePatches.cpp` patches a byte the generated model does not know
   about - i.e. a hole in the model. `EXTRAS` are expected and are the
   point of the exercise.

   > ### ⚠ AMENDED 2026-08-03 - `MISSES 0` IS NO LONGER THE WHOLE CRITERION
   >
   > `crosscheck.py` now has **three** not-a-pass buckets, and the "done"
   > box above still shows only `crosscheck  MISSES 0`. Read the full
   > summary line instead:
   >
   > ```
   > SUMMARY: 268 CodePatches entries = 251 adjudicated (251 passed, 0 MISSED)
   >          + 8 deferred + 9 skipped
   > ```
   >
   > * **MISSES** - a real hole. Must be 0.
   > * **SKIPPED (9)** - questions this gate does not ask (a style GUID is
   >   not a rect). Named and printed. **Not passes.**
   > * **DEFERRED (8)** - questions it *does* ask but cannot answer because
   >   **the model on disk predates the patch**. Named, printed, guarded
   >   G1-G4, and self-expiring. **Not passes either.**
   >
   > **MISSES is 0 today partly because eight sites were RECLASSIFIED, not
   > because the model covers them.** Those eight are the #57 graph-legend
   > sites (`0x76E0E8/E145/E1D6` blocks + `0x76E233/239/23C/2AF/2C8`
   > immediates), all owned by **`sub_76D3D0`** - a builder this stage has
   > never censused. **The regeneration that closes them is the one command
   > block at the top of this file**, plus one edit first: add `0x76D3D0`
   > to `EXTRA_BUILDERS` in `census.py:200`, beside the structurally
   > identical `0x7A04F0`. Guards G1+G2 then revoke the deferral by
   > themselves and the entries come back as passes - or, for the three
   > BLOCK sites, as honest MISSES, because `constants.json`'s `encodings`
   > table models single immediates only and has no schema for a rebuilt
   > instruction block. **Either outcome is information; the deferral is
   > not.** This is exactly the "a skip is never a pass" hazard the same
   > session minted a law about, so it is written here rather than left in
   > the tool's output.

`crosscheck.py` reads `..\..\src\CodePatches.cpp` **read-only**. That file
is edited by other sessions, so the EXTRA count moves; re-run the tool
rather than trusting a quoted number.

## Tier generality comes free

The tables are emitted from the STOCK values, so one run per tier tells
you up front which sites cannot hold `round(stock x f)` in their field:

| tier | file | sites that exceed their field |
|---|---|---|
| 1.5x | `generated-sites-1.5x.txt` | 17 |
| 2x | `generated-sites-2x.txt` | 19 |
| 3x | `generated-sites-3x.txt` | 24 |

Each of those needs a clamp or a runtime pin, and each is flagged inline
with `!!` in the generated text.

## This folder has SIBLINGS (other sessions, later stages)

`tools\uimap\emu\` and `tools\uimap\diff\` are **stages 3 and 4**, built by
other sessions. They keep their own `state.json` and their own `RESUME.md`
inside their own folder - this file and `..\state.json` govern stages 1+2
only. `builders.json` and `constants.json` are their inputs, so treat
those two schemas as a published interface: extend, do not rename.

## Files

| file | what |
|---|---|
| `common.py` | exe/PE mapping, `State` manifest, `FuncMap` |
| `scan_text.py` | stage 1a - `.text` call/jmp edge index, sharded |
| `build_funcs.py` | stage 1b - function map (32,113 functions) |
| `argscan.py` | the arg + encoding extractor (no CLI; imported) |
| `census.py` | **stage 1** -> `builders.json`, `BUILDER-CENSUS.md` |
| `constants.py` | **stage 2** -> `constants.json`, `CONSTANT-MAP.md` |
| `crosscheck.py` | model vs `CodePatches.cpp` (miss / extra) |
| `gen_codepatches.py` | emits C++ site-table TEXT (never edits any .cpp) |
| `fn.py` | ad-hoc: disassemble a function, list callers/callees |
| `pe_probe.py` | prints the PE section table (the mapping proof) |

## Next (stage 3, not built)

`METHOD.md` 6 stage 3 is layout emulation: run a builder under Unicorn
with stubbed window/font APIs and record every create + SetArea, giving a
predicted tree and rects for a given factor. The seeds are in place -
`BUILDER-CENSUS.md` 1 has every primitive signature and arity, and
`tools\flyout-sim\emu_plot.py` / `emu_hittest.py` are the working Unicorn
harness pattern.
