# `winner_table.py` — which file actually wins, for any Plugins layout

Answers one question, per TGI, for a Plugins tree you name: **which file does
SimCity 4 actually load last, and therefore use?**

It exists because every load-order claim in a package redesign ("move this dat
there and it still wins") is a claim about the DBPF merge, and nothing in this
repo could measure that for a layout other than the one currently installed.

* `tools\itemicons\coverage_by_loadorder.py` gets the rule right but only for
  ItemIcons, only on the live tree.
* `tools\dbpf\who_owns_tgi.py` gets the rule right for one TGI, but resolves
  `plugins_dir(require=True)` at import — it can only ever answer for the tree
  that happens to be installed.

Neither can answer *"if I move these files, what changes?"* — which is the only
question a release gate asks.

## The rule it implements

```
game archives  ->  <install>\Plugins  ->  <Documents>\SimCity 4\Plugins
```

and inside each Plugins tree, at every directory level, **FILES load before
SUBFOLDERS**, each group alphabetically. For a duplicate TGI the **last loaded
wins**. A root dat can therefore never override a subfolder dat — which is why
overrides of another mod's data ship from `zzz-SC4UIScale\`.
(`README.md:272`, `docs/BUILDING.md:82`.)

Ordering *among* the stock archives follows the list `who_owns_tgi.py` has
always used (`SimCity_1..5`, `EP1`, `SimCityLocale`), with anything else found
in the install root — `Intro.dat`, `Sound.dat`, an expansion — appended
alphabetically rather than dropped. That order only decides **which** stock
archive gets named when two of them carry the same TGI; it can never change
whether a Plugins file wins, because every Plugins file outranks every archive.

## Commands

```
python winner_table.py                                  # live tree, readable table
python winner_table.py --tree D:\stage\Plugins          # ANY tree
python winner_table.py --diff A\Plugins B\Plugins       # THE RELEASE GATE
python winner_table.py --diff A\Plugins B\Plugins --ignore-moves
python winner_table.py --json
python winner_table.py --selfcheck                      # controls only; exit != 0 = red
```

| flag | meaning |
|---|---|
| `--tree PATH` | the Plugins tree to resolve (default: live user tree via `sc4paths`) |
| `--diff A B` | emit only TGIs whose winning file changes, `TGI  A-winner  ->  B-winner` |
| `--ignore-moves` | `--diff` only: hide keys whose winner is the same **filename** in a new folder, leaving only real changes of owner |
| `--game PATH` | install root (default: `sc4paths.game_dir()`) |
| `--no-game` | skip stock archives and `<install>\Plugins`; the report says so, loudly |
| `--keys` | `ours` (default — every TGI our packages carry, stashed tiers included), `ours-loaded` (only the staged tier), `all` (every TGI on disk) |
| `--only` | filter printed rows: `contested`/`ours`/`third`/`stock`/`none` (counts always cover everything) |
| `--limit N` | max rows printed, `0` = no limit |
| `--json` | machine-readable |
| `--skip-selfcheck` | report without verifying the instrument (prints a loud banner to stderr) |

### Why `--ignore-moves` exists

Relocating one package rewrites the winner **path** of every key it owns.
Moving `DialogStatic-3x.dat` from `010-SC4UIScale\` to `zzz-SC4UIScale\`
produces 265 diff lines that all say the same thing — and buries the six keys
whose *owner* actually changed hands from CAM. The per-key lines stay (they are
the diffable artefact); the **transition summary** printed after them collapses
the noise, and `--ignore-moves` drops pure relocations entirely.

```
--- transitions ---
   259  010-SC4UIScale\z_SC4UIScale_DialogStatic-3x.dat  ->  zzz-SC4UIScale\z_SC4UIScale_DialogStatic-3x.dat
     5  050-load-first\1 CAM Core\CAM_Extended_Essentials.dat  ->  zzz-SC4UIScale\z_SC4UIScale_DialogStatic-3x.dat
     1  050-load-first\1 CAM Core\CAM_Intro.dat  ->  zzz-SC4UIScale\z_SC4UIScale_DialogStatic-3x.dat
```

Read: moving DialogStatic into `zzz-` takes six `.UI` scripts back off CAM.

## `.x1-disabled` is not a special case

`ScaleTier` stashes an inactive tier by renaming `foo.dat` →
`foo.dat.x1-disabled`. The game has no list of stash suffixes: it loads a file
if the file's **final extension** is a DBPF extension, and `.x1-disabled` is not
one. The tool models exactly that, so `.compare-off`,
`.double-load-disabled` and any future suffix are excluded for free, and
`FontStyle.ini.x1-disabled` (an ini, not a dat) is correctly ignored either way.

Stashed files **of ours** are still opened, but only to build the key universe
(`--keys ours`): a release gate has to answer for the tiers that are on disk,
not just the one staged tonight. They never become providers, so they can never
win.

## The positive controls

A winner table reporting zero contested keys is indistinguishable from a table
whose parser silently returned nothing, and this project has paid for that
twice (#140's confident "not in any archive", #139's Rail icon). So the tool
**refuses to print a table** until three things it must be able to see have been
seen. They run before every report, not just under `--selfcheck`.

| | control | what a failure would mean |
|---|---|---|
| **a** | `ZCarbonUI-*` and `DialogStatic-*` contest **197** keys per tier, and the comparator puts ZCarbonUI last | the load-order comparator or the DBPF index parse is broken, or the packages changed |
| **b** | at least one CAM-owned **`.UI`** script outranks our DialogStatic package | the tool cannot see type-`0x00000000` entries, or it does not order `050-load-first\` after `010-SC4UIScale\` |
| **c** | the game's archives are reachable **and** at least one merged key is won by a stock archive | the report is silently Documents-only |

Control **a** compares the two packages' *nominal* ranks, not the loaded set:
on this machine every ZCarbonUI tier is `.x1-disabled` (Carbon skin off), so a
check written against loaded files would measure nothing and call it a pass.

Control **b** is deliberately a **pairwise** check, not a "third party wins"
count. Our own `zzz-SC4UIScale\z_SC4UIScale_CamUI-3x.dat` wins those keys back
from CAM — that is the whole point of shipping them from `zzz-` — so a
global count of third-party winners is legitimately **zero** and would make a
useless control.

Each control prints the numbers it measured. **A control that cannot find its
subject fails**; it never passes by absence.

### The pinned 197

`EXPECT_ZCARBON_DIALOG = 197` was measured on 2026-08-29 across all three tiers
by intersecting the two packages' DBPF indices: 197 keys, of which 88 are
`0x856DDBAC` (PNG) and 109 are `0x00000000` (`.UI`). ZCarbonUI is a strict
subset of DialogStatic's 265.

If that number moves, **the packages changed**. Re-pin it only after reading the
bytes and understanding which entries appeared or vanished — never to make the
control go green.

### Negative controls (all verified 2026-08-29)

Each control was made to fail on purpose, because a gate that cannot fail
proves nothing:

* **a** — pinned value perturbed to 198 → `*** FAILED ***`, printing the
  measured 197 against the expectation for each tier.
* **b** — pointed at a tree holding our package but no CAM → `*** FAILED ***`
  ("NO CAM file outranks it on any of its 265 keys"); and at an empty tree →
  `*** FAILED ***` ("no DialogStatic package on disk — control is a null").
* **c** — `SC4_GAME_DIR` pointed at an empty directory → `*** FAILED ***`
  ("holds NO archives"), `SELFCHECK: RED`, exit 1.

### Cross-check

For `{0x00000000, 0x96A006B0, 0x2A554F6D}` this tool and the independently
written `tools\dbpf\who_owns_tgi.py` agree on both the provider count (4) and
the winner (`zzz-SC4UIScale\z_SC4UIScale_CamUI-3x.dat`). Two separate walks,
two separate archive lists, same answer.

## Exit codes

| code | meaning |
|---|---|
| 0 | green |
| 1 | a positive control failed — the tool refused to report |
| 2 | the named tree does not exist |

Read-only. Never writes to the game or Plugins directories. Never launches the
game.
