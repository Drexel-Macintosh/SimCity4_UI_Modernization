# research — the distilled tier

Three kinds of document, in increasing order of how much they assume:

| | |
|---|---|
| **[laws/](laws/)** | 50 engineering notes, each one paid for by a defect that reached the screen. Start here if you want the rules without the machinery |
| **[UNKNOWNS-AND-NEXT-TARGETS.md](UNKNOWNS-AND-NEXT-TARGETS.md)** | The unknowns register: what is documented well enough to rely on, what is genuinely open and ranked, what was closed as impossible — and the refutation record behind each |
| **[KNOWN-LIMITATIONS.md](KNOWN-LIMITATIONS.md)** | What the mod does not do, and why |
| **[START-HERE.md](START-HERE.md)** | Orientation for research work specifically. Contributor orientation (build, deploy, engineering rules) is [../START-HERE.md](../START-HERE.md) |

The full engine reference — the SDK Maxis never shipped — is in
[../tools/research/](../tools/research/). The per-screen decompilation status
is [../docs/DECOMPILATION-STATUS.md](../docs/DECOMPILATION-STATUS.md).

## Why the laws are the most transferable part

The address lists here are specific to one 2003 executable. The laws are not.
They are what a decade of other people's reverse-engineering would have taught
you, learned instead by shipping something wrong:

- A probe that finds nothing has found nothing **until you prove it could have
  seen the thing**. Most of the expensive mistakes in this project were nulls
  trusted without a positive control.
- Two instruments agreeing count as **one** unless they can fail differently.
- A defect visible only in shipped data is a **hypothesis** until something on
  screen disagrees.
- **Suppression identifies; scaling does not.** Eleven subsystems were closed
  by elimination after every "make it bigger" test returned an ambiguous "no
  change" — while one "make it stop" test named the drawer in a single launch.
- The **symbol is the anchor; the line number is not.**

The register's §G collects the rest, and explains why the refutation record —
the list of theories that turned out wrong — is the part most worth reading.
