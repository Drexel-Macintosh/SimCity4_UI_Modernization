---
name: feedback-null-is-not-evidence
description: "A probe finding NOTHING is not a fact until you prove the instrument could have seen the thing; the costliest form is the SCOPE NULL - a tool answering a narrower question than asked while sounding absolute (3 shipped SC4 defects in one day) — six nulls in one SC4 session were all blind spots, not findings."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-31T19:59:36.953Z
---

**Earned 2026-07-30 (SC4 pause-border hunt). Six probes returned nothing.
Every single null was a BLIND SPOT, not a fact:**

| probe | why the null meant nothing |
|---|---|
| full-screen window scan | walked ONE root; the suspects lived under the other |
| same, both roots | only 2 levels deep; the suspects were deeper |
| `FLASHSET` | sat 52 lines below the `continue` that skipped every flyout |
| `VisTrace` v1 | logged only visibility FLIPS — a window CREATED on the event was silently baselined |
| `EdgeBlt` | the hook it depends on installs LAZILY and had never installed |
| `EdgeBlt`, armed | the hooked class **never draws to the screen** — every dest was panel-sized, so the target could not appear in principle |

The last two are the sharpest: **same detector, same zero, two completely
different reasons, and neither was "the thing doesn't happen."**

**THE RULE — before reporting "X does not happen", state the positive control:**
what WOULD this instrument have printed if X *did* happen, and has it ever
printed that? Cheap controls that work:
- a **primed/heartbeat line with a count** (`VIS primed - 840 windows
  baselined`) proves the walk ran and how much it covered;
- **prove the hook is installed** before believing what it did not see;
- **dump the destinations/scope the hook actually sees** — that one check is
  what exposed the wrong-surface null.

**When reporting, separate STRUCTURAL nulls from MEASURED ones.** A structural
null belongs in the write-up as "could not have seen it" and must never sit in
the evidence column. Saying so cost nothing and kept a wrong conclusion out of
the docs twice in one night.

---

**⛔ THE SCOPE NULL — 2026-07-31, THREE SHIPPED DEFECTS FROM ONE SHAPE.** The
most expensive null is not an empty probe, it is a **tool that answers a
NARROWER question than the one asked** while its output sounds absolute:

| the tool said | it had scanned | what was true |
|---|---|---|
| our doubled script is deployed, the dialog still opens 1x → "the game bypasses the DBPF override" | stock vs ours, never *every dat on disk* | a mod owned the script (5 days lost) |
| art TGI "exclusive to our targets, safe to double in place" | a **stock-only** `.UI` corpus | nine CAM scripts were invisible; six were our own targets |
| `find_tgi.py`: "NOT PRESENT in any shipped archive → **DANGLING**" | the seven **game archives**, no Plugins | CAM shipped the art; a guard was relaxed on that null and the loading screen tiled 4x |

**"Not in the corpus I scanned" and "does not exist" are different statements,
and the second one is almost never what you measured.** Before believing a
tool's absence answer, say out loud what it actually enumerated.

**Fix the WORDING, not just the scan.** `find_tgi.py` now refuses to print the
word *dangling*; it states what it scanned and names the tool that scans wider.
A confident word in an instrument's output becomes a fact in the next
conclusion — the "DANGLING" string is what got copied into a build guard.

**And when a guard has to be relaxed, that is the moment to widen the check,
not narrow it.** Anything the relaxed guard can no longer account for should be
FATAL: the 4x splash was produced by a guard that chose to stay silent.

Sibling failure mode, same family: **an instrument that logs a STATE lies about
WHEN, and one that logs an INPUT never shows the OUTPUT** — see
[[feedback-sc4-measure-dont-infer]] item 6/6b. And: a defect that appears only
on the FIRST use of a session is almost always an uninitialised LATCH, not a
race.

Canonical write-up: `tools\research\METHOD.md` "YOUR OWN INSTRUMENTS CAN LIE".

Related: [[feedback-sc4-measure-dont-infer]], [[feedback-docs-are-the-sdk]],
[[feedback-sc4-blast-radius]].
