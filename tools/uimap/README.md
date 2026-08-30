# uimap — the offline model of SimCity 4's UI layout

This directory answers layout questions **without launching the game**. It
reads `SimCity 4.exe` 1.1.641.0 read-only, finds the code that builds each
window, records the geometry constants that code uses, and emulates what a
layout will do at any scale factor. That is what makes a claim like "this
button is 44 px because of a `push 44` at this address" checkable by anyone
with the same binary, instead of by whoever happened to be watching the
screen.

The engine documentation these tools support is in
[../research/](../research/); the per-screen status page is
[../../docs/DECOMPILATION-STATUS.md](../../docs/DECOMPILATION-STATUS.md).

## The pipeline

Three stages, each writing a database the next one reads. Every derived file
records the exe fingerprint (a truncated SHA-256 plus byte size) it was built
from, and refuses to be trusted against a different binary.

| Stage | Command | Produces |
|---|---|---|
| 1 — census | `python census.py --resume --discover` | `builders.json` — which functions build UI, how they were found, and every primitive call site inside them. Written up in [BUILDER-CENSUS.md](BUILDER-CENSUS.md) |
| 2 — constants | `python constants.py --resume --factor 2.0` | `constants.json` — every geometry constant those builders use, with its encoding, role and twins. Written up in [CONSTANT-MAP.md](CONSTANT-MAP.md) |
| 3 — emulation | see [emu/README.md](emu/README.md) | the layout emulator and the gate suite |

`funcs.json` is the function-start database the whole pipeline indexes
against. `state.json` holds run state and is deliberately local-only.

## The gates

`crosscheck.py` is the load-bearing one: it asks whether the **generated**
model reproduces the **hand-written** patch list in `src/CodePatches.cpp`,
matching by byte coverage. A site the code patches that the model does not
know is a hole in the model. Its header carries the forensic record of every
time that answer changed and why — including the file-age race that turned a
green run red in an afternoon.

Two rules it enforces on itself are worth stating, because they are what make
a green run mean anything. A **skipped** entry is not a pass: it is a question
the gate does not ask, and every skip carries the measured reason and the
observation that would re-open it. A **deferred** entry is not a pass either:
it is a question the gate asks but cannot answer yet, and four guards revoke
the deferral automatically the moment the excuse expires.

The 21 `gate_*.py` files in [emu/](emu/) adjudicate specific families — the
combined-families gate, for instance, proves no two byte-patch families write
overlapping bytes, and fails on any patch table nobody registered, so a new
family cannot be silently invisible to it.

## Reference documents

| Document | What it settles |
|---|---|
| [coverage-matrix.md](coverage-matrix.md) | The authoritative coverage census. The canonical headline is the distinct-root-id figure it states; looser denominators exist and are listed there precisely because quoting them interchangeably once hid a defect for weeks |
| [BUILDER-CENSUS.md](BUILDER-CENSUS.md) | Every builder function, how discovery found it, and what it calls |
| [CONSTANT-MAP.md](CONSTANT-MAP.md) | Every modeled geometry constant, by owner |
| [WINNER-TABLE.md](WINNER-TABLE.md) | Which file actually wins the load order for any given resource |
| [BLIT-BEHAVIOUR.md](BLIT-BEHAVIOUR.md) | What scaled art does to each destination kind |
| [SUBFLYOUT-BUILDER.md](SUBFLYOUT-BUILDER.md) · [SUBFLYOUT-CONSTANTS.md](SUBFLYOUT-CONSTANTS.md) · [SUBFLYOUT-ART-VERDICT.md](SUBFLYOUT-ART-VERDICT.md) · [SUBFLYOUT-LIVE-EVIDENCE.md](SUBFLYOUT-LIVE-EVIDENCE.md) | The nested plop menus, decoded four ways: the builder, its constants, whether the geometry comes from art or code, and the live measurements that adjudicated it |
| [emu/README.md](emu/README.md) | The emulator itself, file by file |
| [emu/POPUP-VERDICT.md](emu/POPUP-VERDICT.md) · [emu/SHOW-PATH.md](emu/SHOW-PATH.md) | Two decoded paths: what the ordinance description popup really does, and the visibility setter |

## Running it cold

The pipeline needs a copy of the game binary and `pip install capstone
unicorn`. The three databases ship with the repository, so the emulator and
its gates run on a fresh clone without regenerating anything; regenerate only
when the patch list changes, and regenerate **deliberately** — never as a side
effect of a gate, because a gate that rewrites the model it is checking has
stopped being independent.
