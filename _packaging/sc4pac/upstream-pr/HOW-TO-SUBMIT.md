# HOW TO SUBMIT

Run these as **Drexel-Macintosh**. `gh auth status` already reports that account
on this machine, so no re-auth should be needed.

Shell: **Git Bash** (the `sed` step is POSIX). A PowerShell alternative for that
one step is given below.

---

## STOP — read this first

Upstream precedent is a **single PR that adds the package file and the
`lint-config.yaml` line together**. Commit `bd7c51ac` ("Add Disable FPS Limit",
PR #164) touched exactly two files:

```
modified lint-config.yaml
added    src/yaml/caspervg/disable-fps-limits.yaml
```

Every one of the five existing `group-to-github` entries corresponds to a group
that already has packages in the channel. A **mapping-only PR has no precedent**
— it would add a mapping for a group that does not exist in the channel, the
linter would never exercise it, and a maintainer has no way to review it. Expect
it to be held until the package arrives.

So the mapping should ride along with the package. **The package is not
publishable yet** — see the blockers in `LINT-FINDINGS` at the bottom of this
file (placeholder sha256, no `v4.5.0` release, probe #202 open). Clear those
first, then run Path A.

Path B (mapping only) is included for the case where memo33 explicitly asks for
the config change as a separate first step.

---

## PATH A — the real submission: package + mapping in one PR

### A1. Fork and clone

```bash
gh repo fork memo33/sc4pac --clone=true --remote=false -- --depth=50
cd sc4pac
```

### A2. Branch

```bash
git checkout -b add-a-drexel-sc4-ui-scale
```

### A3. Add the package file

```bash
mkdir -p src/yaml/a-drexel
cp /c/dev/SC4UIScale/_packaging/sc4pac/drexel-sc4-ui-scale.yaml \
   src/yaml/a-drexel/sc4-ui-scale.yaml
```

Then **strip the internal engineering commentary** from the copy. The working
file carries a long header of measurement notes, an open-probe blocker and
internal TODOs that should not go upstream. Keep the metadata (from `group:`
onward) and any comment that explains a decision a reviewer would otherwise
question — the `a-drexel` sort-order rationale is worth keeping in a short form.

### A4. Add the lint-config line

```bash
sed -i 's/^- caspervg: caspervg$/- caspervg: caspervg\n- a-drexel: Drexel-Macintosh/' lint-config.yaml
```

PowerShell equivalent, if you prefer:

```powershell
$p = 'lint-config.yaml'
(Get-Content $p -Raw) -replace "(?m)^- caspervg: caspervg`r?`n", "- caspervg: caspervg`n- a-drexel: Drexel-Macintosh`n" |
  Set-Content $p -NoNewline -Encoding utf8
```

### A5. Verify before committing

```bash
git diff lint-config.yaml
```

Expect **exactly one added line**:

```diff
+- a-drexel: Drexel-Macintosh
```

Then run the real linter over the whole channel:

```bash
python -m pip install --quiet PyYAML jsonschema python-dateutil
curl -sSL -o /tmp/lint.py https://raw.githubusercontent.com/memo33/sc4pac-actions/main/src/lint.py
python /tmp/lint.py --config lint-config.yaml src/yaml ; echo "exit=$?"
```

Must print `Successfully validated <N> files.` and `exit=0`. **Do not push on a
non-zero exit.**

### A6. Commit

```bash
git add src/yaml/a-drexel/sc4-ui-scale.yaml lint-config.yaml
git commit -m "add SC4UIScale (a-drexel) and its group-to-github mapping"
```

### A7. Push

```bash
git push -u origin add-a-drexel-sc4-ui-scale
```

### A8. Open the PR

```bash
gh pr create \
  --repo memo33/sc4pac \
  --base main \
  --head Drexel-Macintosh:add-a-drexel-sc4-ui-scale \
  --title "Add SC4UIScale (a-drexel) and its group-to-github mapping" \
  --body-file /c/dev/SC4UIScale/_packaging/sc4pac/upstream-pr/PR-BODY.md
```

### A9. Afterwards

The validation workflow **must be triggered manually by the maintainers for
first-time contributors** (`docs/metadata.md`, "Submitting your package"), so a
PR showing no checks is expected, not a failure. Submitting to the main channel
also carries an ongoing commitment to keep the package updated.

---

## PATH B — mapping only (only if memo33 asks for it)

```bash
gh repo fork memo33/sc4pac --clone=true --remote=false -- --depth=50
cd sc4pac
git checkout -b lint-config-a-drexel
sed -i 's/^- caspervg: caspervg$/- caspervg: caspervg\n- a-drexel: Drexel-Macintosh/' lint-config.yaml
git diff lint-config.yaml
git add lint-config.yaml
git commit -m "lint-config: map group a-drexel to GitHub account Drexel-Macintosh"
git push -u origin lint-config-a-drexel
gh pr create \
  --repo memo33/sc4pac \
  --base main \
  --head Drexel-Macintosh:lint-config-a-drexel \
  --title "lint-config: map group a-drexel to Drexel-Macintosh" \
  --body-file /c/dev/SC4UIScale/_packaging/sc4pac/upstream-pr/PR-BODY.md
```

If you use Path B, trim `PR-BODY.md` first — as written it describes the package
too, which would be confusing on a config-only PR.

---

## LINT-FINDINGS — clear these before Path A

Measured by running upstream `lint.py` against
`_packaging/sc4pac/drexel-sc4-ui-scale.yaml` inside a full clone of the channel.

**Lint itself is clean once the mapping is added** — 693 files, exit 0. There is
no second round of lint complaints waiting. Everything below is a
*channel-review / install-correctness* blocker that lint cannot see.

1. **The `sha256` is a placeholder of 64 zeros.** Lint only checks the shape, so
   it passes, but sc4pac verifies extracted-file checksums before moving files
   into Plugins — the install would abort for every user. Must be the sha256 of
   the extracted `SC4UIScale.dll`, not of the zip.

2. **The asset URL points at a release that does not exist.** The yaml declares
   `version: "4.5.0"` and a URL under `.../download/v4.5.0/SC4UIScale-v4.5.0.zip`,
   but the latest published release is **`v4.4.0`** (asset `SC4UIScale-v4.4.0.zip`).
   `gh api .../releases/tags/v4.5.0` returns 404. Publish v4.5.0 first, or point
   the metadata at v4.4.0.

3. **`lastModified` is a placeholder** (`2026-08-29T00:00:00Z`). Should be the
   real release timestamp.

4. **No `nonPersistentUrl`.** `docs/metadata.md` recommends one whenever
   `withChecksum` is used, so update-checking tools can see new releases. Not an
   error, but a likely review comment.

5. **Probe #202 is still open** — the file's own header says not to publish the
   channel entry until it comes back extension-gated. That is a project blocker,
   not an upstream one, but it gates the whole submission.

6. **`config:sc4-edition-windows-digital` resolves fine.** Linting the file
   alone reports it as undefined; that is an artefact of single-file linting.
   The package is real, defined in `src/yaml/config/sc4-edition.yaml`, and the
   error disappears in a full-channel run. No action needed.
