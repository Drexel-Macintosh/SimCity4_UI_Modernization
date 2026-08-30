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

So the mapping should ride along with the package. **Every one-time blocker is
CLOSED** (real sha256s, published release, probe #202 measured extension-gated
— see `LINT-FINDINGS` at the bottom for the record). The submission source is
the LEAN file emitted by `gen_channel.py --publish` into
`_packaging/sc4pac/publish/sc4-ui-scale.yaml`; the annotated internal yaml
never goes upstream (PR #199 shipped it verbatim — that is why the distinction
exists, and why `Submit-PR.ps1`'s pre-flight now refuses the internal file).

Path B (mapping only) is included for the case where memo33 explicitly asks for
the config change as a separate first step.

---

## PATH A — the real submission: package + mapping in one PR

### A1. Fork and clone

```bash
gh repo fork memo33/sc4pac --clone=true --remote=false -- --depth=50
cd sc4pac
```

### A2. Branch — based on UPSTREAM main

```bash
git fetch https://github.com/memo33/sc4pac.git main
git checkout -B add-a-drexel-sc4-ui-scale FETCH_HEAD
```

(`Submit-PR.ps1` does this itself since v4.5.2 — its first real run proved the
old flow never created the branch at all, so a fresh clone committed to `main`
and the push died on a missing refspec.)

### A3. Add the package file

```bash
mkdir -p src/yaml/a-drexel
cp /c/dev/SC4UIScale/_packaging/sc4pac/publish/sc4-ui-scale.yaml \
   src/yaml/a-drexel/sc4-ui-scale.yaml
```

That file is the LEAN output of `gen_channel.py --publish` — already stripped,
already carrying the short load-bearing rationales a reviewer needs (the
`a-drexel` sort order, the payload mechanism, the DLL root note). Never copy
`drexel-sc4-ui-scale.yaml`: that is the annotated internal record, and the
pre-flight refuses it.

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

## LINT-FINDINGS — the original list, ALL CLOSED (kept as the record)

Measured by running upstream `lint.py` inside a full clone of the channel.
**Lint is clean once the mapping is added** — 693 files, exit 0. The
2026-08-29 audit found five install-correctness blockers lint cannot see;
every one is closed, and the closure is enforced by a gate, not by memory:

1. ~~Placeholder sha256~~ **CLOSED** — every entry is computed from the built
   bundle and re-verified off the emitted YAML on every `gen_channel.py` run;
   `Check-ChannelYaml.ps1` (shared by Submit-PR and Test-Sc4pacInstall)
   refuses any zero-hash.

2. ~~Asset URL points at an unpublished release~~ **CLOSED** — the release
   exists, `Build-Dist.ps1` now cuts the zip itself from the gated bundle,
   and the shared pre-flight HEAD-requests the URL before any PR opens.

3. ~~`lastModified` placeholder~~ **CLOSED** — `--publish` refuses to run
   without `--last-modified` (the GitHub release publish time), so the
   upstream file can never carry a bundle-mtime placeholder.

4. ~~No `nonPersistentUrl`~~ **CLOSED, by removal** — the corpus survey
   (2026-08-30) showed the field is for a SECOND host's page (GitHub url +
   Simtropolis nonPersistentUrl) consumed by the STEX/SC4E update checkers.
   GitHub is our only host, so the field is correctly absent.

5. ~~Probe #202 open~~ **CLOSED** — measured 2026-08-30: SC4's plugin scan is
   EXTENSION-gated, so the `.uipay` payload lists are sound and the publish
   embargo is lifted.

6. **`config:sc4-edition-windows-digital` resolves fine.** Linting the file
   alone reports it as undefined; that is an artefact of single-file linting.
   The package is real, defined in `src/yaml/config/sc4-edition.yaml`, and the
   error disappears in a full-channel run. No action needed.
