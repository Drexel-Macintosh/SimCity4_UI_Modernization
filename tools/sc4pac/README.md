# tools/sc4pac

Generates `_packaging/sc4pac/drexel-sc4-ui-scale.yaml` — the sc4pac channel
metadata for this mod — from a **built bundle**.

```
python tools/sc4pac/gen_channel.py --bundle dist/SC4UIScale-v4.5.0-dev
```

The output file is generated. Do not hand-edit it; edit the generator.

## Why it is generated

The v4.5.0 payload layout ships one live `z_SC4UIScale_<Pkg>.dat` per package
plus inert `z_SC4UIScale_<Pkg>.<tag>.uipay` files (tags `15x` / `2x` / `3x` /
`on` / `off`). Measured against sc4pac 0.10.0: **a file with a non-canonical
extension installs only through a `withChecksum` entry — listed under
`include:` it is silently dropped.** So all 78 payloads need an individual
entry carrying a real sha256, and those hashes change on every build. That is
not a hand-maintained list.

The design decisions and the full measured record of sc4pac's behaviour live in
the `PRESERVED_*` constants at the top of `gen_channel.py`, copied verbatim from
the hand-written file this replaced. They are reproduced in every generated
output.

## What it emits

| document | subfolder | contents |
| --- | --- | --- |
| `a-drexel:sc4-ui-scale` | `050-load-first` | the DLL (`withChecksum` — it lands at the Plugins root by extension, but include-only installs nothing) plus `Plugins/010-SC4UIScale/` |
| `a-drexel:sc4-ui-scale-mod-overrides` | `900-overrides` | `Plugins/zzz-SC4UIScale/`, depends on the first |
| asset `a-drexel-sc4-ui-scale` | — | the GitHub release zip for the bundle's version |

**The group id `a-drexel` is load-bearing.** sc4pac sorts by `<group>.<name>`
within a subfolder, so `a-drexel` sorts before `cam.*`: this package loads
before CAM and therefore *loses* to CAM per-TGI, which is the compatibility
gate. Renaming it to `drexel` inverts CAM precedence silently. Do not "tidy" it.

**No ini ships.** See the per-file `exclude:` comments in the output for what
each excluded ini was for and what excluding it costs. Two of the four have a
functional cost; `--ship-asset-inis` ships those two (never the user config).

## Self-checks

Every run performs these, and aborts without writing if any fails:

- **COVERAGE** — every file under `<bundle>/Plugins` is claimed by exactly one
  package through exactly one install mechanism. An unclaimed file or folder is
  named and the run fails.
- **CHECKSUM** — every emitted sha256 is re-verified by re-hashing, reading the
  paths back *out of the written YAML* rather than out of memory.
- **STABLE** — the bundle tree is fingerprinted before hashing and again after.
  A rebuild landing mid-run would produce a torn manifest that passes every
  other check; this is the only thing that catches it. (Observed for real on
  2026-08-29.)
- **COMMENTS** — every `#` line in the previous output must still be present.
  Only the volatile `generated:` / `bundle:` banner fields are exempt.
  `--allow-comment-loss` overrides, deliberately and loudly.

## Validating the output

`lint.py` is not vendored here. Fetch it and the channel's config from upstream:

```
curl -O https://raw.githubusercontent.com/memo33/sc4pac-actions/main/src/lint.py
curl -O https://raw.githubusercontent.com/memo33/sc4pac/main/lint-config.yaml
python lint.py --config lint-config.yaml _packaging/sc4pac
```

Two complaints are expected and are **not** defects in this file:

1. `config:sc4-edition-windows-digital ... referenced, but not defined` — that
   check only makes sense for the self-contained main channel. Adding
   `extra-channels: ["https://memo33.github.io/sc4pac/channel/"]` to the config
   resolves it.
2. `GitHub account "Drexel-Macintosh" ... is not known to belong to group
   "a-drexel"` — a `group-to-github` mapping must be contributed to the upstream
   `lint-config.yaml`. **The fix is upstream, not a group rename.** With that
   mapping added locally, lint reports `Successfully validated 1 files.`

To confirm the linter can actually fail, regenerate with a broken group and lint
that copy — it must report the naming-convention violations:

```
python tools/sc4pac/gen_channel.py --bundle <dir> --group A_Drexel --out /tmp/control/drexel-sc4-ui-scale.yaml
python lint.py --config lint-config.yaml /tmp/control
```

## Notes

- The version is parsed from the bundle directory name, never hardcoded. A
  pre-release marker (`-dev`, `-rc1`, …) is stripped for the release tag and
  URL, and the output says so. Override with `--version`.
- `lastModified` defaults to the newest file mtime in the bundle. Re-stamp it
  from the published release asset before the channel goes live.
- The bundle's own `SHA256SUMS.txt` is **not** used as a source. In the
  v4.5.0-dev bundle it still describes the pre-payload layout and is stale.
