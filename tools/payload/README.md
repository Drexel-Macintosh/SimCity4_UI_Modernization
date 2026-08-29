# tools/payload — the content-swap payload builder

Converts the tier-tagged dat layout into the **payload layout** the
stable-filename arming design needs.

## The problem this exists for

The mod arms a scale tier by **renaming its own dats**:

```
z_SC4UIScale_CamUI-2x.dat.x1-disabled   ->   z_SC4UIScale_CamUI-2x.dat
```

sc4pac tracks the files it installed **by exact name** and can only remove
those exact names. AutoScale performs the rename above on the player's *first
launch*, picking whatever tier their screen needs — so by the time anyone
uninstalls, the names on disk are not the names sc4pac recorded. This is the
single reason the package manager cannot uninstall this mod cleanly, and it is
not a rare manual-tier-switch edge case.

The replacement is a **content swap at a stable filename**: one live
`z_SC4UIScale_<Pkg>.dat` per package, never renamed, whose *bytes* the DLL
overwrites from an inert payload file the game never loads.
`src/ScaleTier.cpp` already pilots the DLL half for one package
(`SyncDatStable`, v4.0.3, SelectiveArt). **This tool builds the payload half,
for every package.**

## The two measured facts it stands on

Both from `_tests/Probe-ScanPredicate.py` (#202), measured on this machine —
neither is assumed:

* **SC4's plugin scan is EXTENSION-GATED, not magic-gated.** A real DBPF
  copied to `.uipay` did **not** appear in the game's registered-segment
  census, while our live `.dat` files did. The positive control is the part
  that matters: 13 of our own `.dat` files *were* named in the same census, so
  the census demonstrably could have seen the `.uipay` and did not. `.uipay`
  is therefore inert by extension.
* **A one-entry DBPF loads cleanly and registers as a segment.** That is what
  makes a gated-off package shippable as real content rather than as a missing
  or empty file.

## Usage

```
python tools/payload/build_payloads.py --src <plugins-dir> --out <dir>
python tools/payload/build_payloads.py --verify --out <dir>
```

`--out` is **required** and is never defaulted. This tool never writes to the
player's live Plugins folder, and never writes to `--src`.

| flag | meaning |
|---|---|
| `--src DIR` | Plugins-style source tree, walked recursively. Relative layout (`010-SC4UIScale\`, `zzz-SC4UIScale\`) is preserved in the output, because the subfolder is load-order-significant. |
| `--out DIR` | where payloads are written. Required in both modes. |
| `--verify` | check a produced payload set instead of building one. |
| `--allow-incomplete` | report bases missing tiers without failing the run. |
| `--extra-tree DIR` | fold an additional archive tree into the census (repeatable). |

Typical sources:

```
# from a built release
python tools/payload/build_payloads.py --src dist\SC4UIScale-v4.4.0\Plugins --out _work\payloads

# from the live install (read-only; output still goes to --out)
python tools/payload/build_payloads.py --src "%USERPROFILE%\OneDrive\Documents\SimCity 4\Plugins" --out _work\payloads
```

## What it emits

For every package base `z_SC4UIScale_<Pkg>`:

```
z_SC4UIScale_<Pkg>.15x.uipay    byte-for-byte copy of <Pkg>-15x.dat
z_SC4UIScale_<Pkg>.2x.uipay     byte-for-byte copy of <Pkg>-2x.dat
z_SC4UIScale_<Pkg>.3x.uipay     byte-for-byte copy of <Pkg>-3x.dat
z_SC4UIScale_<Pkg>.off.uipay    a one-entry DBPF that contests nothing
```

`.x1-disabled` is stripped when reading, so **it does not matter which tier
happened to be armed** on the machine the sources came from. Every copy is
re-hashed after writing and the digests recorded — a copy is proven, not
inferred from the absence of an exception.

Also written: `payload-manifest.json` — source path, byte count and SHA-256 for
every payload, plus the `.off` TGI assigned to each package.

### The four package shapes

The layout is not uniform, and inventing tiers for the packages that do not
have them would ship art that does not exist.

| category | detected by | emitted |
|---|---|---|
| **full tier set** | has `-15x`, `-2x`, `-3x` | `.15x` / `.2x` / `.3x` / `.off` |
| **inverse-gated** | has only `-1x` | `.on` / `.off` |
| **tier-independent** | no tag at all | **nothing** — reported only |
| **incomplete** | some but not all tiers | **nothing** — reported, run fails |

*Inverse-gated* is `z_SC4UIScale_SelectorUI-1x`, the one package armed by the
**absence** of a tier (`ScaleTier.cpp: SyncSelectorPackage`). It carries the
scale selector at stock geometry, and it is what keeps 1x from being a one-way
door — at 1x every other package is stashed, so without it the only way back up
would be editing the ini by hand. It gets `on`/`off`, never a scale name.

*Tier-independent* are the string-only packages — `WebText`,
`CamGraphLabels`, `MenuFix`. A string has no geometry, so there is nothing to
scale and nothing to gate; their `.dat` name is already stable and sc4pac can
already remove it. No payload is invented for them.

*Incomplete* fails the run by default: half a payload set is a package that
silently loses a tier. `--allow-incomplete` skips them knowingly.

One trap handled explicitly: a base with tier tags **and** a bare `.dat` (that
is SelectiveArt today) is a full tier set, not a tier-independent package — the
bare file is the *live stable target* of the pilot swap, not a source.

## The `.off` payload — why it is what it is

A gated-off package still needs a **live file at the stable name**, because the
whole point is that the name never changes. That file may not be empty or
content-free:

* `_packaging/Build-Dist.ps1` **hard-throws** on shipping one. That guard is
  defect #182: an empty `FontStyle.ini` got snapshotted as the user's original
  and the game took an ACCESS_VIOLATION.
* sc4pac **aborts an install outright** when a shipped `.dat` fails to parse as
  DBPF.

So the `.off` payload is a **valid one-entry DBPF** whose single TGI is unique
per package and verified absent from every archive the game can see — a live
file that loads, parses, and declares nothing anyone else owns.

Details, each chosen rather than defaulted:

* **Type `0x856DDBAC` / Group `0x6A386D26`** — not invented here. This is the
  exact Type/Group the #202 probe packed and booted, so the shape measured to
  load cleanly is the shape that ships.
* **Instance** — one per package, from the reserved window
  `0x5C4B0000–0x5C4BFFFF`. The starting point is a SHA-256 digest of the
  package's own relative path, not a counter and not Python's randomised hash,
  so a rebuild does not churn the shipped TGI. A previous run's choice is read
  back out of `payload-manifest.json` and reused when it is still free.
  Collisions — against the merged index or against another package in the same
  run — are resolved by walking forward in the window.
* **Body: a real 1x1 transparent PNG**, built in code so it is auditable
  rather than pasted. Type `0x856DDBAC` *means* PNG in SC4, and the game stores
  that type as plain uncompressed PNG (`tools/dbpf/NOTES-PACK.md`). The probe
  proved a one-entry archive registers with arbitrary bytes in it; making the
  bytes match their declared type costs nothing and removes the only way a
  correctly-typed reader could ever choke on the file.
* **Built with `tools/dbpf/DbpfPack.exe`**, the project's own DBPF writer — no
  second archive format in the tree. What it produced is then read back and
  asserted to be exactly the one entry that was asked for; the writer's exit
  code is not taken as proof.

## Controls

### The census control (mandatory, both modes)

Every `.off` TGI must be **absent** from the merged index of every archive the
game can see. An absence is worthless if the index is empty — and a false zero
of exactly that shape has shipped in this project twice. So before any absence
is believed, the census is asserted large, and the numbers are printed every
run:

```
merged index census: 927267 TGI(s) from 288 archive(s); 36 unparsable
  reference (measured 2026-08-29, this machine): 927267 TGI(s) / 288 archive(s)
CONTROL PASSED: the census demonstrably read the installed archives, so an
absence in it is real evidence.
```

Below the floor (50 archives / 50,000 TGIs — the same numbers
`Probe-ScanPredicate.py` refuses below, so the two tools agree on what "we
actually looked" means) the tool **refuses to run**.

The index parse itself is **imported** from `_tests/Probe-ScanPredicate.py`
(`read_index` / `merged_index`), never re-implemented. A third copy of that
loop would be a third place for it to drift out of agreement with the archives
it describes. The import is done with bytecode caching disabled so it leaves
nothing behind in `_tests/`.

Trees walked: the user's `Documents\SimCity 4\Plugins` (both package folders and
everything else in it), the game's own `Plugins`, and the game install
directory holding the retail archives — plus anything passed with
`--extra-tree`.

### `--verify`

Checks a produced payload set and **exits non-zero naming the check that
failed**:

| check | asserts |
|---|---|
| **(a)** | every base has a complete payload set — `{15x,2x,3x,off}` or `{on,off}`, nothing else |
| **(b)** | every `.uipay` parses as a DBPF |
| **(c)** | every `.off.uipay` has exactly one entry |
| **(d)** | no two `.off` payloads share a TGI |
| **(e)** | no `.off` TGI appears anywhere in the merged index |

(c) reads the entry **count out of the header** as well as the parsed index,
because `read_index` returns a *set* and would silently collapse a duplicate
TGI into one.

`--verify` finding no payloads at all is treated as a **refusal**, not a pass.

### Negative controls run against `--verify` (2026-08-29)

A passing check is not evidence until it has been shown it can fail. Each check
was broken deliberately and fired on exactly its own condition:

| broken | result |
|---|---|
| deleted `CamUI.2x.uipay` | `(a) incomplete set … has {15x,3x,off}` |
| overwrote a payload's DBPF magic | `(b) not a parseable DBPF` |
| repacked an `.off` with two entries | `(c) .off is not one entry … header count 2` |
| copied one `.off` over another | `(d) duplicate .off TGI … both own T-0x856DDBAC_G-0x6A386D26_I-0x5C4B963A` |
| repacked an `.off` at a TGI the game already owns | `(e) .off TGI is CONTESTED` |
| pointed the census at an empty tree | `REFUSING: the census looks too small (0 archives, 0 keys)` |
| removed one tier from the source | `INCOMPLETE TIER SETS — NOT EMITTED`, exit 1 |

## What this tool does not do

It builds the payload **files**. It does not modify `src/`, and the DLL does not
read `.uipay` yet — extending `SyncDatStable` from the SelectiveArt pilot to
every package, sourcing bytes from `.uipay` instead of from permanently-suffixed
`.dat.x1-disabled` files, is the next step and is not part of this tool. It also
does not touch `_packaging/`; wiring payloads into `Build-Dist.ps1` and the
package manifest is separate work.

It never launches the game, never writes to the live Plugins folder, and never
writes anywhere but `--out`.
