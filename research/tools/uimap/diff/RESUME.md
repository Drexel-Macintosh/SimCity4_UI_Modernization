# RESUME — tools\uimap\diff

## The one command

```
cd "<proj>\tools\uimap\diff"
python diff.py --auto --resume --write-findings
```

That is the whole contract. It is safe to run at any time, from any state,
as many times as you like:

- `--resume` reuses any census whose source log is byte-for-byte unchanged
  (fingerprint = abspath + size + mtime, recorded in `state.json`).
- Without `--resume` everything is recomputed **and the output is identical**
  — there is no wall-clock, no `dict` iteration order and no PRNG anywhere in
  the output path. Re-running from scratch is never wrong, only slower.
- `state.json` is rewritten after **every** unit, not at the end, so an
  interruption loses at most one unit.

Delete `state.json`, `report.json`, `census\` and `FINDINGS-generated.md` at
any time; they are all regenerated.

**Where the findings live.** `FINDINGS-generated.md` is the machine digest
(regenerated every run). The hand-written ANALYSIS — what the first run
actually found, with the evidence and the HYPOTHESIS labels — is
`tools\research\_checkpoints\uimap-stage4-diff.md`, which is where METHOD.md
section 3 routes agent work and audit digests. **Read that one first.**

## Units (what `--resume` skips)

| Unit id | Work |
|---|---|
| `parse:<logname>` | one log -> `census\<log>.census.json` |
| `stock:scripts` | the 330 extracted stock `.UI` scripts |
| `stock:thirdparty` | mod-replaced `.UI` scripts (these WIN for ids they declare) |
| `stock:<logname>` | an inert (f=1) census used as measured stock |
| `triage:UiSpike.cpp` | the never-scale id arrays, parsed read-only from source |
| `model` | the predicted model under `tools\uimap\` |
| `diff:event_check` | scale-event self-check |
| `diff:<logname>:f=<f>` | live-vs-stock for one log at one factor |
| `tiersweep:f=<f>` | offline tier-generality pass |
| `report` | `report.json` |

## Useful variants

```
python diff.py --auto --history         # include the .bak-*/.prev archive.
                                        # Those are up to 20 versions old, so
                                        # every fix since reads as a defect.
                                        # Use to VALIDATE the detector, not to
                                        # triage today.
python diff.py --auto --factor 1.5      # judge the same logs against another tier
python diff.py --tier-sweep             # tier generality only, no logs needed
python diff.py --auto --fail-on any     # exit 1 if anything is unexplained
python diff.py --auto --include-hidden  # drop the on-screen gate (floods)
python parse_log.py <log> --out census  # parse only
```

## What is still missing, and what to do when it lands

**The PREDICTED source (stages 1-3) did not exist when this was built.**
`tools\uimap\` held only `pe_probe.py`. `diff.py` reports
`model_available: false` with a reason and skips section C; everything else
runs. When `builders.json` / `constants.json` / `emu\*.json` appear, just
re-run the command at the top — nothing needs editing.

### The schema `load_model()` accepts

Deliberately permissive, because the emitting agents had not fixed a
contract yet. Any of these is understood:

```jsonc
// a bare list
[ {"id": "0x0423278F", "l": 0, "t": 0, "w": 500, "h": 277, "factor": 1.0} ]

// or wrapped under any of: windows | predicted | tree | rects | nodes
{ "windows": [ { ... } ] }

// or keyed by id
{ "0x0423278F": {"w": 500, "h": 277, "parent": "0x0423278E"} }
```

Per-window fields, all optional except the id:

| Field | Accepted spellings |
|---|---|
| id | `id`, `win_id`, `window_id`, `wid` — hex string or int |
| rect | `{l,t,w,h}` or `{x,y,w,h}` or `{w,h}` or `area: [l,t,r,b]` or a bare `[l,t,r,b]` |
| parent | `parent`, `parent_id` |
| factor | `factor` — **the factor the predicted rect is stated at.** Default 1.0 |
| builder | `builder`, `builder_va`, `va` |

`factor` matters: the model-vs-stock check asserts the model's own claim
equals `round(stock * factor)`, so a model emitted at f=1 and a model emitted
at f=2 are both checkable without a flag.

If stages 1-3 emit something else, adapt **`_extract_windows()` in
`diff.py`** — it is the single adapter point, and nothing else in the file
knows the model's shape.

## Reading the output

`report.json` is the full join. `FINDINGS-generated.md` is its readable
digest. Verdicts, worst first:

| Verdict | Meaning |
|---|---|
| `STOCK-1X` | live size == stock while f != 1 — **the scaler missed it** |
| `OVER-SCALED` | live == round(stock*f*f) — scaled twice |
| `MISMATCH` | neither law reproduces the live size; delta reported |
| `RECURRING-*` | seen correct, then wrong AGAIN — REGRESSION.md law 14 class |
| `PRE-SWEEP` | wrong only BEFORE the first correct sighting — benign timing |
| `MATCH` | live == round(stock*f) |
| `SCREEN-SIZED` | sized by the render resolution, not by f |
| `AMBIGUOUS-ID` | generic id (<= 0xFF); identity not establishable by id |
| `UNKNOWN-STOCK` | no stock oracle for this id — cannot judge, not a pass |

## Constraints this tooling operates under

- **OFFLINE ONLY.** Never launches, attaches to or kills SimCity 4.
- The Plugins folder and every log in it are **READ ONLY**.
- Writes only under `tools\uimap\diff\`.
- `Documents` is OneDrive-redirected on this machine; the path is resolved at
  runtime, never hardcoded.
