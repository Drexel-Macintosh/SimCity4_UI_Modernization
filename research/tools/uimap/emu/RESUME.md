# RESUME — continue the Stage-3 layout emulator

**Status at last write: COMPLETE and green — 5 pass / 0 fail.** Nothing is
half-finished. This file exists so an interrupted or repeated run costs
nothing.

## The one command

```
cd "<repo root>\tools\uimap\emu"
python emu_layout.py --selftest --resume
```

* `--resume` skips every case already marked `done` in `state.json`.
* Add `--fresh` to discard `state.json` and re-run everything from scratch —
  always safe, nothing is destructive.
* Add `-v` to see every recorded `SetArea` / `GZWinMoveTo` / `FitWindowToText`.

Expected output ends with:

```
acceptance: 5 pass, 0 fail, 0 skipped
```

(or `0 pass, 0 fail, 5 skipped` when resuming an already-complete state).

## Continue a builder scan

```
python emu_layout.py --builder=0x78B980 --len=0x140 --parent=840x125 --resume
python emu_layout.py --builder=0x77C1C0 --len=0x120 --parent=840x125 --resume
```

Call-site disassembly is cached in `cache\callsites-*.json`; delete a cache
file to force a re-scan of that range.

## Where things are

| Want | Read |
|---|---|
| the answer to the popup question (geometry + the wrap flag) | `POPUP-VERDICT.md` |
| task #50, the 1x flash: the visibility setter and where to hook it | `SHOW-PATH.md` |
| how to point it at a new builder | `README.md` |
| per-case results / what already ran | `state.json` |
| narrative status for a cold agent | `..\..\research\_checkpoints\uimap-stage3-emu.md` |

## The one thing still open

`POPUP-VERDICT.md` §5: **nobody has ever seen this popup at 1x.** Three
minutes with `_tests\Restore-StockPark.ps1` (procedure in
`BUDGET-DETAIL-ANATOMY.md` §POPUP P5) decides whether stock wraps the
description or clips it like we do. The §4 fix is correct either way; that
capture only decides whether anything *further* is needed.
