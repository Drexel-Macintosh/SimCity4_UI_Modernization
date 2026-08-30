# PATCH — one line to `lint-config.yaml`

## The file

| | |
|---|---|
| Repository | **`memo33/sc4pac`** (the metadata channel), *not* `memo33/sc4pac-actions` |
| Path | **`lint-config.yaml`** — repository root |
| Key | **`group-to-github`** |
| Pinned against | repo HEAD `fd06c203` (2026-08-28); this file last touched in `35e6b8a8` (2026-06-14) |

`memo33/sc4pac-actions` holds the linter *code* (`src/lint.py`) but contains **no**
`lint-config.yaml`. The config that governs the public channel lives in the channel
repo and is passed in with `--config`. Confirmed by listing both repo trees.

## The exact YAML shape (verified, not assumed)

`group-to-github` is a **YAML sequence of single-key mappings** — `group: github-owner`.
It is *not* a plain mapping. Proven by `src/lint.py` lines 569–570, which iterate the
list and then iterate each element's items:

```python
for d in self.config['group-to-github']:
    for group, gh_owner in d.items():
```

The list is in **append (chronological) order, not alphabetical** — see the existing
entries below. The new entry therefore goes at the **end** of the list.

## Current content (lines 30–36)

```yaml
group-to-github:
- null-45: "0xC0000054"
- simmaster07: nsgomez
- memo: memo33
- nam: NAMTeam
- caspervg: caspervg

```

## After the change

```yaml
group-to-github:
- null-45: "0xC0000054"
- simmaster07: nsgomez
- memo: memo33
- nam: NAMTeam
- caspervg: caspervg
- a-drexel: Drexel-Macintosh

```

## Unified diff

```diff
--- a/lint-config.yaml
+++ b/lint-config.yaml
@@ -30,6 +30,7 @@ group-to-github:
 - simmaster07: nsgomez
 - memo: memo33
 - nam: NAMTeam
 - caspervg: caspervg
+- a-drexel: Drexel-Macintosh
 
 # The following is only appropriate when nobody can make unnoticed changes to
 # the metadata checksum fields.
```

Exactly one line added. No quoting needed on either side — `"0xC0000054"` is quoted
only because it would otherwise parse as a number. The file is LF, ASCII, no BOM;
keep it that way.

## Why the value is `Drexel-Macintosh`

Lint compares the **owner segment of the asset's download URL**, nothing else — not
the `info.author` field, not the `website` field, not the git remote.

`src/lint.py` line 266 defines the pattern, capturing the owner as group 1:

```python
gh_url_pattern = re.compile(r"^https://github\.com/([^/]+)/(?:[^/]+)/releases/download/.*")
```

`src/lint.py` lines 576 and 581 apply it to the asset's `url` and take group 1 —
**this is the line that decides the string**:

```python
m = self.gh_url_pattern.fullmatch(self.asset_urls[asset])
...
gh_owner = m.group(1)          # line 581
```

and line 582 tests that captured string against the configured set for the group:

```python
if gh_owner not in grp2gh.get(group, set()):
```

The asset URL in the generated yaml is the versioned release download:

```
https://github.com/Drexel-Macintosh/SimCity4_UI_Modernization/releases/download/v<version>/SC4UIScale-v<version>.zip
```

so group 1 captures `Drexel-Macintosh` regardless of the release version.
Running the real `lint.py` against the real
file reproduces it verbatim:

```
GitHub account "Drexel-Macintosh" for asset "a-drexel-sc4-ui-scale" is not known to
belong to group "a-drexel" (a new mapping needs to be defined in lint-config.yaml).
```

The comparison is a plain set membership test on the captured substring, so it is
**case-sensitive and must match the URL byte-for-byte**: `Drexel-Macintosh`.

### About the `JoeLiTrenta` in the original error

That string came from an **earlier revision of the package yaml whose asset URL
pointed at a different account**. It is not a fact about lint and must not be
carried into the patch:

- `gh api users/JoeLiTrenta` returns **HTTP 404** — no such GitHub account exists.
- `gh api repos/Drexel-Macintosh/SimCity4_UI_Modernization/releases` lists real
  releases (`v4.4.0`, `v4.3.1`, `v4.3.0`, …).

Adding `JoeLiTrenta` would map the group to a non-existent account and leave the
real one still failing. The correct value is `Drexel-Macintosh`.

## Measured effect of the patch

Full-channel lint, our package file dropped into `src/yaml/a-drexel/`, against
upstream `lint-config.yaml` **unpatched**:

```
===> DLLs should be downloaded from the author's GitHub releases to ensure authenticity.
GitHub account "Drexel-Macintosh" for asset "a-drexel-sc4-ui-scale" is not known to
belong to group "a-drexel" (a new mapping needs to be defined in lint-config.yaml).
Finished with 1 errors.          exit code 1
```

Same run with the one line added:

```
Successfully validated 693 files.
exit code 0
```

That single line is the whole fix — no other upstream change is required.
