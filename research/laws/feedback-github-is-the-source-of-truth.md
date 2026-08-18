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

Related: [[feedback-a-package-is-not-done-until-its-in-the-manifest]] — same
failure shape one level up. A package absent from the manifest does not ship;
a file absent from the repo does not survive.
