---
name: feedback-github-is-the-source-of-truth
description: USER ORDER — the SC4UIScale GitHub repo is canonical. Every session ends with a commit and push. A finding that is not committed does not exist.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-18T13:35:31.784Z
---

**The repo is the project. Work that is not pushed is work that can vanish.**

Repo: `sc4uiscale`, PRIVATE, on the user's GitHub account. Established
2026-08-18 after an audit found the repo carried **2.8% of files and 1.2% of
bytes** of the working tree — and, worse, was missing three of the eight package
builders and three hand-authored build inputs. It could build the DLL and not
the art. Nobody knew until it was measured.

**Why:** the project is a multi-month reverse-engineering effort against a
closed-source game. Its value is not the source — that rebuilds in minutes — it
is the 105 scaling laws, the ledger of refuted hypotheses, and the derived
lists. All of that was single-copy on one machine, inside a OneDrive folder,
with no history.

**How to apply:**
- **End every working session with a commit and push.** Not "when it's tidy" —
  every session. Ledger entry and commit are ONE action, not two.
- **A defect closed but not committed is not closed.** The ledger, the code and
  the repo state move together or the ledger is lying.
- **When adding any file the build reads, ask whether a cold clone would have
  it.** Three builders were missing precisely because nobody asked.
- **Never commit Maxis-derived art.** The principle is: *the repo carries
  knowledge, code and derived lists; the player's own game install supplies the
  art.* Derived lists and hand-authored inputs DO belong in the repo — the ones
  that were missing could not be regenerated from anything.
- **Run the privacy gate before pushing** (`_packaging/Test-NoForeignContent.py`).
  Machine paths leak through research notes constantly; 41 files needed
  sanitising on the first pass.
- **Mirror the memory corpus.** `MEMORY.md` → `research/laws/INDEX.md`, and the
  memory files → `research/laws/`. ⚠ Do NOT mirror by name prefix — the first
  attempt used `*sc4-*` globs and silently missed
  [[project-sc4touchcontrols-independence]] (no hyphen after `sc4`) and
  [[feedback-scale-the-mods-own-dialogs]] (SC4-only content, generic name).
  Select by CONTENT, not filename.

⚠ **Still owed as of 2026-08-18:** the working tree is to be relocated out of
OneDrive and git-init'd in place with an ALLOWLIST-shaped `.gitignore`
(`/*` then `!` re-includes). Until that lands there are still two trees and
drift is still possible. See [[project-sc4uiscale-github-publish]] and the
approved plan. Task #108 rejected in-place git in OneDrive for three reasons
that still hold: a ~200:1 excluded:shipped ratio makes a denylist unsafe, there
is a nested `.git` clone under `tools/research/submenus-dll-src/`, and OneDrive
locks `.git` objects mid-write.

## PRESENCE IS NOT EXECUTION (2026-08-18, cost: 5 of 9 builders)

An audit verified all the package builders were **present** in the repo and
called the gap closed. A cold-clone test then **ran** them and five of nine
refused - every one on a missing INPUT, not missing code:

- `tools/dbpf/extracted-png-tgi.csv`, `tools/uiscripts/extracted/`,
  `tools/dialog-static/thirdparty-src/`, `tools/dialog-static/thirdparty-art/`
  - all four correctly absent (the player's own game and mod files), all four
  derived by **nothing**, and each failing with a bare `FileNotFoundError`
  naming a path a successor has never heard of.
- A dependency ORDER nothing enforced: `selective-safe` emits what
  `dialog-static` and `stage_icons` read, so running the set as a flat list
  fails for the wrong reason.

**How to apply:** a "the repo has everything" claim is only worth what you
EXECUTED. Run the thing from a cold clone; do not check that the file exists.
The audit's own verdict on the csv was "regenerable, does NOT affect the
build" - and it was wrong, because the builder read it at a path extraction
never creates. Cures now in-repo: `tools\Bootstrap-Corpus.ps1` derives every
input, `_tests\Test-Builders.ps1` runs all nine in dependency order.

⚠ **Our own installed packages are a confounder in any "what does the game
load" computation.** With them present, `winning_corpus.py` reports
*third party: 0* and the mod scripts are invisible. Exclude `z_SC4UIScale_*`
and `zzz-SC4UIScale\` from any load-order scan - and remember ScaleTier
renames disabled tiers to `.x1-disabled`, so a `*.dat`-only scan misses them.

⭐ **A 2x package is an exact inverse of its 1x source.** Nearest-neighbour at
an integer factor is losslessly invertible, so 1x art lost from Plugins can be
recovered from our own shipped 2x dat by taking every other pixel. PROVEN, not
assumed: 30 of the 129 ItemIconsSub sources exist nowhere on this machine but
inside our own packages; the inversion was verified 99/99 exact on the ones
that DID survive before being trusted on the 30, and the result is 129/129
pixel-exact. Byte-compare fails there (PIL re-encodes the PNG) - compare
PIXELS. See [[feedback-sc4-scaling-laws]].

## THE MANIFEST FINDS THINGS THE AUDIT DIDN'T (2026-08-18, same day)

Cross-checking builders against `_tests/Deploy-OnGameClose.ps1` (the
authoritative deploy manifest, per its own header) instead of trusting a
remembered inventory turned up THREE more real, live-deployed packages that
had never been counted anywhere: MenuFix, CsiIcons, NamIcons. The lesson isn't
"count better" - it's that a manifest is the only list that can't silently
drift, because the game reads it.

⭐ **A cold clone that builds does not mean the LIVE install matches it.** A
full per-entry payload comparison (direct DBPF index reads - see
`dbpf_direct.py` shape: parse the header at 0x24/0x28/0x2C, don't trust a
packer's own `--extract` naming, it was non-deterministic) between a fresh
cold-clone build and this machine's actual deployed packages found real
differences at every turn, and every one of them meant the DEPLOYED copy was
STALE relative to current source (a leftover credits LTEXT, pre-fix
`imagerect` values, a 1.5x corpus that predates a producer-sentinel
correction) - never the reverse. **The DLL being freshly rebuilt today says
nothing about whether the ART packages were rebuilt at the same time**; they
are a separate, more expensive step and drift out of sync easily. Byte
differences alone are not evidence of a real defect either: PNG
re-compression changes bytes without changing pixels - decode and compare
PIXELS before calling something a content difference.

Also confirmed: `Test-NoForeignContent.py` has PRIVATE vs PUBLIC modes for a
reason. In private mode, cross-project name hits are advisory; in `--public`
mode they correctly fail the build. `research/laws/INDEX.md` (this project's
mirror of the whole cross-project MEMORY.md) currently trips the public gate
on Surface-hardware and other sibling-project entries - that is the gate
working as designed, not broken, and it is exactly what "audit before public
release" (already a tracked pending item) exists to clean up. Don't mistake a
correct FAIL on `--public` for a bug.

Related: [[feedback-a-package-is-not-done-until-its-in-the-manifest]] — same
failure shape one level up. A package absent from the manifest does not ship;
a file absent from the repo does not survive.
