# A Null Needs a Positive Control

A probe that finds nothing is not a fact. It becomes a fact only once the
instrument is shown to be capable of seeing the thing it failed to see. In a
closed-source engine, most nulls are blind spots.

## Six nulls from one hunt, all blind spots

A single investigation into an unexplained border artifact produced six probes
that returned nothing. Every one of them was structurally incapable of
observing the target:

| probe | why the null meant nothing |
|---|---|
| full-screen window scan | walked one root; the suspects lived under the other |
| same scan, both roots | descended only two levels; the suspects were deeper |
| `FLASHSET` | sat 52 lines below a `continue` that skipped every flyout |
| `VisTrace` v1 | logged visibility *flips* only — a window created already-visible on the event was silently baselined |
| `EdgeBlt` | the hook it depends on installs lazily and had never installed |
| `EdgeBlt`, armed | the hooked class never draws to the screen — every destination was panel-sized, so the target could not appear in principle |

The last two are the sharpest case: the same detector, the same zero, two
completely different reasons, and neither reason was "the thing does not
happen."

## The rule

Before reporting "X does not happen", state the positive control: what would
this instrument have printed if X *did* happen, and has it ever printed that?

Cheap controls that work:

- **A primed/heartbeat line carrying a count** — `VIS primed - 840 windows
  baselined` proves the walk ran and states how much ground it covered.
- **Prove the hook is installed** before believing anything it did not see.
  Lazily-installed hooks are a guaranteed null until first use triggers them.
- **Dump the destinations or scope the hook actually sees.** Printing the
  observed destination rectangles is what exposed a hook watching a class that
  never reaches the screen.

## Structural nulls versus measured nulls

Separate the two when writing anything up. A structural null belongs in the
narrative as "could not have seen it" and must never sit in the evidence
column. Labelling it costs nothing and keeps wrong conclusions out of the
record.

## The scope null

The most expensive null is not an empty probe. It is a tool that answers a
*narrower* question than the one asked, while its output sounds absolute.

| the tool reported | what it had actually scanned | what was true |
|---|---|---|
| a doubled script is deployed yet the dialog still opens 1x, therefore "the game bypasses the DBPF override" | stock content versus the mod's own content — never every `.dat` on disk | a third-party mod owned the script |
| an art TGI is "exclusive to the mod's targets, safe to double in place" | a stock-only `.UI` corpus | nine CAM scripts were invisible to the scan; six of them referenced the same targets |
| `find_tgi.py`: "NOT PRESENT in any shipped archive, therefore DANGLING" | the game archives only, with no `Plugins` tree | CAM shipped the art; a build guard was relaxed on that null and the loading screen tiled 4x |

"Not in the corpus I scanned" and "does not exist" are different statements,
and the second is almost never what was measured. Before believing a tool's
absence answer, say out loud what it enumerated.

## Fix the wording, not just the scan

A confident word in an instrument's output becomes a fact in the next
conclusion — the literal string `DANGLING` is what got copied into a build
guard. `find_tgi.py` therefore refuses to print the word *dangling* at all; it
states what it scanned and names the tool that scans wider.

## Relaxing a guard is the moment to widen the check

When a guard has to be relaxed, anything the relaxed guard can no longer
account for should become fatal rather than silent. The 4x splash screen was
produced by a guard that chose to stay quiet about what it had stopped
checking.

## Sibling failure modes

- An instrument that logs a *state* lies about *when*; one that logs an *input*
  never shows the *output*.
- A defect that appears only on the first use of a session is almost always an
  uninitialised latch, not a race.
