# UI coverage matrix — authoritative census

**Rewritten 2026-08-03** by reconciling three independent inventories (roots /
crosscheck / live-evidence) against a fresh count taken from source. Supersedes
`tools\research\_checkpoints\coverage-matrix.md` (2026-07-29), which stays in
place as the historical record. **This file is now the one to read.**

> # ⛔ SUPERSEDED 2026-08-03 EVENING — ~~THE CANONICAL HEADLINE IS **67.5%**~~
>
> ### ⛔ SUPERSEDED 2026-09-01 — ~~RE-MEASURED 2026-08-16: THE CANONICAL HEADLINE IS **73.5%**~~
>
> **Retired, not merely re-measured — the reason matters.** `86/117` counted ONE
> of the mod's four delivery mechanisms: an id literal in `src\UiSpike.cpp`. It
> is blind to the staged dialog-static path (seven player-facing dialogs that
> ship PRE-SCALED), to shipped ART plus a deliberate structural skip, and to
> coverage held through a host/child relationship rather than through the root
> id. Its denominator also carried 27 root ids the retail game cannot
> instantiate. Both errors ran the same way — understating the numerator,
> overstating the denominator — which is how the figure stood for a month.
>
> ### **CURRENT — 90/90 = 100% *of RETAIL-REACHABLE stock .UI roots*.**
>
> **The scope phrase is PART OF THE NUMBER.** "100% of the UI" is FALSE and must
> never be written here: the code-created window channel is unbounded and this
> metric does not touch it. The tool prints the phrase with the ratio for exactly
> that reason (the `SCOPE_PHRASE` constant in `coverage_rederive.py`).
>
> ### **CURRENT — 93/117 = 79.5% over ALL distinct nonzero root ids.**
>
> Kept beside the headline so the 27 exclusions stay auditable instead of
> vanishing into a denominator. Every excluded id prints on every run with its
> class and its named mechanism (`EXCLUDED_ROOTS`), under a ceiling that FAILS
> the run if the list grows past it (`MAX_EXCLUSIONS = 27`). A denominator that
> shrinks silently is the same defect as a numerator that grows silently.
>
> **Verified by re-running `python tools\uimap\coverage_rederive.py` on
> 2026-09-01.** It prints, in order:
> `COMBINED: 93/117 DISTINCT root ids reached = 79.5%`,
> `denominator  117 total - 27 unreachable = 90 retail-reachable`,
> `numerator    90 reached by either mechanism`,
> `==> 90/90 = 100.0% of RETAIL-REACHABLE stock .UI roots`.
> The tool is the authority, not this file — never hand-compute a coverage figure
> to replace one here.
>
> ⚠ **The tool still MEASURES and prints `86/117 = 73.5%` on every run, and that
> is deliberate** — the figure is left standing so no previously-quoted number
> moves silently. As of 2026-09-01 it prints under the label `SUPERSEDED
> HEADLINE - retired 2026-09-01, still measured:`. It is the SINGLE-MECHANISM
> figure, not the headline. Quote it only as *"86 root ids are named in
> `UiSpike.cpp`"*.
>
> ⚠ **The D1 and D1+D2 rows in the comparison table below are retired too.** D1's
> `288/298 = 96.6%` was published for a month against §4's own 2026-08-16
> instruction to re-derive "10 root slots / 9 distinct ids" before quoting it.
> That instruction was executed for the first time on 2026-09-01 and all nine
> gaps had closed — six genuinely, and three (`0x6BFAC122`, `0x8BFAC13E`,
> `0xCBFACAE1`) were being counted COVERED WITHOUT BEING COVERED, on membership
> in `kOwnsBackgroundSheet` (grep it in `src\UiSpike.cpp`), a DERIVED array they
> qualify for on art data alone while the windows are never created. D2 was
> re-measured the same day from 11/17 to 13/17 on its own 17-window denominator.
> Both re-derivations are recorded in `_tests\REGRESSION.md` under "2026-09-01 —
> D2 re-measured" and "2026-09-01 — D1 re-derived".
>
> **Everything else in this box is the 2026-08-16 record, kept as written and
> annotated in place. This block outranks it.**
>
> **User decision, 2026-08-03: the STRICTEST view is canonical.**
>
> ~~**67.5% — 79 of 117 DISTINCT root ids carry a scaling mechanism.**~~
>
> ### ~~**73.5% — 86 of 117 distinct root ids are named in `UiSpike.cpp`.**~~
>
> ⛔ **SUPERSEDED 2026-09-01 — see the CURRENT block at the top of this box.**
> Retired because it counted ONE delivery mechanism of four, not because it
> drifted: "named as a `0x........` literal in `src\UiSpike.cpp`" was never the
> same question as "does this root ship scaled", and it misses the **7** roots
> reached only by the staged dialog path. The current figures are
> **90/90 = 100% *of RETAIL-REACHABLE stock .UI roots*** and **93/117 = 79.5%
> over ALL roots**. 73.5% was true for its own scope on 2026-08-16 and the 86 it
> reports is now only part of a numerator.
>
> **The 2026-08-16 record below is kept as written. It was true on its date; the
> CURRENT block at the top of this box outranks it.**
>
> **Corrected 2026-08-16.** The tool this box names as the sole authority
> ~~now prints~~ **printed, on that date,**
> `CANONICAL COVERAGE: 86/117 DISTINCT root ids named = 73.5%` and
> `[OK ] distinct root ids named    floor 83   measured 86  (IMPROVED - raise the
> floor to 86)`. ⚠ **The floor line still emits verbatim; the `CANONICAL
> COVERAGE:` label does not.** As of 2026-09-01 the tool prints the same 86/117
> figure under `SUPERSEDED HEADLINE - retired 2026-09-01, still measured:` — the
> number is deliberately unchanged so nothing previously quoted moves silently,
> but it is no longer labelled canonical. Its own floor comment records the first
> step — `# v2.65.0 (#54): 79 -> 83` (~~`coverage_rederive.py:234`, floor value at
> `:244`~~ — **re-anchored 2026-09-01: those line numbers no longer resolve, the
> file has grown. Grep the tool for `v2.65.0 (#54): 79 -> 83` and for
> `"distinct_root_ids_named"` in the `COVERAGE_FLOOR` block instead of citing a
> line**). The further move to 86 was above the floor and is recorded only by the
> run. The denominator was unchanged at 117, so only the numerator moved. Nothing
> regressed.
>
> **"Covered" is weaker than "carries a scaling mechanism."** The tool defines it
> as *the id appears as a `0x........` literal somewhere in `src\UiSpike.cpp`*
> (`coverage_rederive.py:992-995`) — it does not include the dialog-static staged
> path and does not exclude dev-editor or plugin roots. Three of the ids gained in
> the 79 → 83 step got there by entering `kNeverScaleIds`
> (`coverage_rederive.py:234-235`) — named in order NOT to be scaled. Do not read
> this metric as "N roots are scaled".
>
> **Read the rest of that floor comment before quoting either number.** Against
> **the 38 uncovered ids the #54 census examined**, 20 are SC4's own DEVELOPER
> TOOLS (Script Console / Breakpoints / Call Stack / Variables / Script View / Lot
> Configuration Editor / Select Prop|Building|Flora Families / Set Compatibilities
> / Configure Columns / Simulator Control), 8 are scaled in DATA where this grep
> cannot see them, 3 are MEASURED ABSENT from the shipping image, and 2 are
> code-created or dev twins — **in-scope coverage is ~87/92**
> (`coverage_rederive.py:236-243`). ⚠ That split (20+8+3+2 = 33) was taken when 38
> ids were uncovered; **31 are uncovered today** (117 − 86), so it does not
> re-apply to the current set without re-running the census. Do not read the 26.5%
> remainder as "a quarter of the UI is broken" — most of that denominator must
> NEVER be scaled.
>
> ⚠ The comparison table below carried `79/117 = 67.5%` as **CANONICAL**; it was
> corrected in the same 2026-08-16 pass — read that table's own note with it.
>
> Produced by `python tools\uimap\coverage_rederive.py`, which is now the ONLY
> tool allowed to state a coverage figure. Nothing regressed. We stopped
> counting the flattering way.
>
> **Why this number and not the others.** Four views existed and were being
> quoted interchangeably, which is exactly how #99 hid for weeks:
>
> | view | ratio | |
> |---|---|---|
> | **retail-reachable roots, either mechanism** | **90/90 = 100%** — *of RETAIL-REACHABLE stock .UI roots* | ⬅ **CANONICAL from 2026-09-01** — the scope phrase is PART OF THE NUMBER. "100% of the UI" is FALSE: the code-created channel is unbounded and no part of this census touches it. 27 of the 117 roots are removed as ones retail cannot instantiate (Lot Editor 11, Lua debugger 5, exemplar editor 4, Simulator Control, 3 dead Move In My Sim variants, 3 singletons), each printed every run with its class, its mechanism and a positive control — `EXCLUDED_ROOTS` in `coverage_rederive.py`, hard ceiling `MAX_EXCLUSIONS = 27`, scope string in `SCOPE_PHRASE` |
> | the same numerator over ALL roots | **93/117 = 79.5%** | kept so the 27 exclusions stay auditable — 86 named in `UiSpike.cpp` + 7 reached only via the staged dialog path |
> | **DISTINCT root ids named** | ~~**79/117 = 67.5%**~~ ~~**86/117 = 73.5%**~~ | ⛔ **SUPERSEDED 2026-09-01** — held ⬅ CANONICAL from 2026-08-16 until this date. RETIRED BECAUSE it counted only ONE delivery mechanism: "covered" meant *the id appears as a `0x........` literal in `src\UiSpike.cpp`* and nothing else, so it was blind to the staged dialog path that reaches SEVEN further ids shipping PRE-SCALED — and its denominator still carried all 27 retail-unreachable roots. The tool deliberately still measures and prints this figure so that no previously-quoted number moves silently; it is no longer the figure to quote |
> | roots whose root id is named | ~~293/337 = 86.9%~~ **302/337 = 89.6%** | instance count, not id count — re-measured 2026-08-16 |
> | any subtree id named | ~~295/337 = 87.5%~~ **304/337 = 90.2%** | weakest test — re-measured 2026-08-16 |
> | D1 script-declared roots | ~~288/298 = 96.6%~~ — **RETIRED 2026-09-01** | different denominator (script-declared shipping roots) — see below. **Re-derived 2026-09-01: the first execution ever of §4's 2026-08-16 instruction to "re-derive '10 root slots / 9 distinct ids' before quoting either"** (298 − 288 = those same 10 slots). All nine gaps had closed — six genuinely, and **three were being counted COVERED without being covered**: they sit in `kOwnsBackgroundSheet`, a DERIVED array they qualify for on art data alone while the windows are never created (`_tests\REGRESSION.md`, "2026-09-01 — D1 re-derived"). **Retired because its numerator was wrong, not merely unrefreshed** — the old status cell claimed only that it had not been re-measured. Superseded by **90/90 = 100% *of RETAIL-REACHABLE stock .UI roots*** and **93/117 = 79.5% across ALL distinct stock root ids**, both printed by a `coverage_rederive.py` run of 2026-09-01. The scope phrase is part of the number: **"100% of the UI" is FALSE**. |
> | D1+D2 (the old headline) | ~~299/315 = 94.9%~~ **RETIRED 2026-09-01** | ⛔ Not merely un-re-measured — **retired**. This cell used to say only "NOT re-measured 2026-08-16", which is how it survived a month. It WAS re-measured on 2026-09-01 and **both components moved**, so their sum cannot stand. **D2 is 13/17 = 76.5%** (was 11/17 = 64.7%: `0x00000043` gained a cure in v4.5.3, and `0xEA659793` was a grading artefact — it is the sweep walk root, whose two structural twins were already graded COVERED for that same reason). **D1's "10 root slots / 9 distinct ids" was re-derived for the first time** — all nine gaps were already closed, and **three had been counted COVERED without being covered**, on membership in `kOwnsBackgroundSheet`, a DERIVED array they qualify for on art data alone while the windows are never created. **No replacement figure is stated on this denominator.** `coverage_rederive.py` does not compute D1/D2 — it explicitly refuses the comparison — and it is the only tool permitted to state a coverage figure, so do not hand-compute the sum. **The current figures, each inseparable from its scope:** `90/90 = 100.0% of RETAIL-REACHABLE stock .UI roots` (117 total − 27 proven retail-unreachable) and `93/117 = 79.5% over ALL roots`, kept so the exclusions stay auditable. **"100% of the UI" is FALSE** — the unbounded code-created channel lies outside this denominator entirely. Evidence: `_tests\REGRESSION.md`, "2026-09-01 — D2 re-measured" and "2026-09-01 — D1 re-derived". |
>
> ⚠ **SUPERSEDED 2026-09-01 — this paragraph reports a run that no longer
> reproduces. Kept as the record of what was believed on 2026-08-16; do not
> quote its figures.**
>
> > ~~⚠ **RE-MEASURED 2026-08-16 — all three tool-derived rows had drifted UP.**
> > `python tools\uimap\coverage_rederive.py` prints `302/337 = 89.6%`,
> > `304/337 = 90.2%` and `CANONICAL COVERAGE: 86/117 DISTINCT root ids named =
> > 73.5%`, OVERALL PASS, with the denominators unchanged (`roots with a nonzero
> > id= : 337`, `DISTINCT nonzero root ids : 117`).~~
>
> **Three separate things in it went stale, for three different reasons.** All
> readings below are from a `python tools\uimap\coverage_rederive.py` run on
> 2026-09-01; nothing here was hand-computed.
>
> **1 — `86/117 = 73.5%` is RETIRED as the headline.** The tool still measures
> and prints it, and its floor check still reads `[OK ] distinct root ids named
> floor 83   measured 86  (IMPROVED - raise the floor to 86)` — nothing
> regressed. But "named" means only *the id appears as a `0x........` literal in
> `src\UiSpike.cpp`*, so a root reached by the staged dialog path scores as
> uncovered. The same run prints the two figures that replace it, **each
> inseparable from its scope**: **`90/90 = 100.0% of RETAIL-REACHABLE stock .UI
> roots`** (built from `denominator  117 total - 27 unreachable = 90
> retail-reachable`, with all 27 removals listed by name and mechanism every run)
> and **`COMBINED: 93/117 DISTINCT root ids reached = 79.5%`** over ALL roots.
> ⛔ **The scope phrase is PART OF THE NUMBER. "100% of the UI" is FALSE.**
>
> **2 — `302/337 = 89.6%` and `304/337 = 90.2%` are unquotable at any
> denominator.** This run measures `1037/1075` and `1039/1075`, but the
> denominator's own check FAILS: `[FAIL] roots with nonzero id  expected 337
> measured 1075   <- CORPUS-SIZE class` (this machine's plugin set differs from
> the baseline). Per the tool's own banner, **do not quote a number whose own
> check failed** — so neither the 337-based pair nor the 1075-based pair may be
> re-quoted. What survived is `[OK ] distinct nonzero root ids expected 117
> measured 117`, which is exactly why every live figure in this box is an **id**
> count over 117 and not an instance count.
>
> **3 — "OVERALL PASS" is stale.** The run ends `!! OVERALL: FAIL - 6 hard
> expectation(s) diverged.` Every one is CORPUS-SIZE class — the installed plugin
> corpus, not a parser regression; the distinct-id checks the 90/90 and 93/117
> figures rest on all read `[OK ]`.
>
> **The 2026-08-03 figures were correct on their date — they are not a
> mis-quote.** They were measured that day (`coverage_rederive.py:229`) and
> frozen as the tool's regression FLOORS (`coverage_rederive.py:231-245`:
> `293` / `295` / `83`). Coverage then improved and only the floors were left
> behind; every run since has said so out loud, printing
> `(IMPROVED - raise the floor to 302 / 304 / 86)` on all three
> (`coverage_rederive.py:1047-1049`). **A floor is a lower bound that has stopped
> tracking. Re-run the tool; never quote these cells.**
>
> The CANONICAL row fell furthest because it drifted twice: #54/v2.65.0 already
> raised that floor 79 → 83 (`coverage_rederive.py:234`, "v2.65.0 (#54): 79 ->
> 83") without this table being touched, and it measures 86 today. ~~Read `coverage_rederive.py:234-243` before quoting 73.5% as a defect
> rate — 20 of the roots it counts uncovered are SC4's own developer tools and 8
> are scaled in data this grep cannot see.~~
>
> ### ⛔ SUPERSEDED 2026-09-01 — do NOT quote 73.5% as a defect rate at all.
>
> That instruction is retired because it taught the reader to keep quoting a
> figure whose denominator AND numerator were both known to be wrong, softened
> by a caveat. **73.5% = 86/117 counted ONE delivery mechanism of four** — an id
> appearing as a `0x........` literal in `src\UiSpike.cpp` — so every root
> reached by the staged dialog-static path scored as a miss, and every root the
> retail game cannot open stayed in the denominator. The cure is the
> re-derivation, not a caveat on the old ratio. ⚠ **Its anchor is also dead:**
> `:234-243` no longer holds the #54 census, which now lives in the
> `COVERAGE_FLOOR` comment block — grep the tool for `v2.65.0 (#54): 79 -> 83`
> rather than citing a line number, and note that the census was taken when 38
> ids were uncovered, so it is HISTORY.
>
> **CURRENT — and neither figure may be stated without its scope**
> (`python tools\uimap\coverage_rederive.py`, run 2026-09-01):
> **90/90 = 100.0%** *of RETAIL-REACHABLE stock .UI roots*, and **93/117 = 79.5%**
> over ALL distinct root ids with the exclusions included. The run prints
> `denominator  117 total - 27 unreachable = 90 retail-reachable` then
> `==> 90/90 = 100.0% of RETAIL-REACHABLE stock .UI roots`. **The scope phrase is
> PART OF THE NUMBER** (`SCOPE_PHRASE` in the tool): "100% of the UI" is FALSE and
> must never be written — the code-created channel is unbounded and untouched by
> this count. The 27 removed roots are `EXCLUDED_ROOTS`, each with a named
> mechanism, an empirical positive control and the reading that would put it back,
> under the hard ceiling `MAX_EXCLUSIONS = 27`.
>
> ⛔ ~~**D1 and D1+D2 were NOT re-measured** and are left exactly as written.~~
> **SUPERSEDED 2026-09-01 — both WERE measured, and neither was left as written.**
> The struck sentence was accurate about the 2026-08-16 pass and is kept as the
> record of it; it is struck because it is the sentence a reader uses today to
> conclude that the D1 and D1+D2 rows in the table above still stand. They do not.
>
> * **D1 — ~~288/298 = 96.6%~~ is RETIRED, not merely stale.** §4's own 2026-08-16
>   instruction to re-derive "10 root slots / 9 distinct ids" *before quoting
>   either* was executed for the first time on 2026-09-01. **All nine gaps had
>   closed** — six genuinely, and **three were being counted COVERED without
>   being covered**: `0x6BFAC122`, `0x8BFAC13E`, `0xCBFACAE1` qualify for the
>   DERIVED array `kOwnsBackgroundSheet` on art data alone while **the windows
>   are never created**. A numerator holding three roots that render nothing is
>   not repaired by re-running it, so 96.6% is withdrawn rather than re-stated.
> * **D2 — ~~11/17 = 64.7%~~ re-measured 2026-09-01 to 13/17 = 76.5% of
>   code-created NAMED shipping windows.** `0x00000043` (Restore-Toolbars) and
>   `0xEA659793` (region screen) are covered; the total only *looked* static
>   because two long-covered windows left the predicate as those two entered.
>   **D1+D2 = ~~299/315 = 94.9%~~ is therefore retired too** — both terms moved.
> * **Quote instead, scope attached.** `python tools\uimap\coverage_rederive.py`
>   printed on 2026-09-01 `denominator 117 total - 27 unreachable = 90
>   retail-reachable` and **`90/90 = 100.0% of RETAIL-REACHABLE stock .UI
>   roots`**, with **`COMBINED: 93/117 DISTINCT root ids reached = 79.5%`** over
>   ALL roots, kept so the 27 exclusions stay auditable. **The scope phrase is
>   part of the number — "100% of the UI" would be FALSE**, the unbounded
>   code-created channel being untouched by any of this.
>
> **What has not changed:** D1/D2 came from the dialog-static +
> `tools\uimap\wincensus.py` route, which this tool still does not compute and
> still explicitly refuses to be compared against. ⚠ The
> `coverage_rederive.py:992-999` anchor the struck sentence cited for that
> refusal is **stale** — those lines are corpus-size expectations today; grep the
> tool for "NOT comparable" instead.
>
> ### ⛔ SUPERSEDED 2026-09-01 — half of this sentence was RETRACTED
>
> The claim as it stood, kept so what was believed stays readable, now struck:
> ~~**"The 96.6% and 94.9% figures below are NOT wrong, and they are NOT
> comparable to 73.5%."**~~ (It originally read 67.5%; the comparison figure was
> corrected to 73.5% on 2026-08-16.)
>
> **"NOT comparable" still stands. "NOT wrong" does not.** Those two figures
> count *script-declared shipping roots* plus code-created windows; the
> distinct-id figure counts *distinct root ids* — 117 of them — which is a
> different denominator, not a check on the first. Quoting one against the other
> was the original #99 error and the sections below still invite it. **Do not do
> that arithmetic.** The instrument prints the same warning on every run.
>
> **Why "NOT wrong" was retracted.** §4's own 2026-08-16 amendment instructed
> "re-derive '10 root slots / 9 distinct ids' before quoting either". It was
> executed for the first time on **2026-09-01**, and **D1's numerator did not
> survive it.** All nine gaps had closed — six genuinely — and **three had been
> counted COVERED without being covered**: `0x6BFAC122`, `0x8BFAC13E` and
> `0xCBFACAE1` sit in `kOwnsBackgroundSheet`, a DERIVED array they qualify for on
> the art data alone, **while the windows are never created**. An id in a derived
> list is evidence about the DATA, not about whether anything renders. D2 moved
> in the same pass — 11/17 = 64.7% → **13/17 = 76.5%** — so 299 is wrong in the
> same breath as 288.
>
> **96.6% (288/298, D1) and 94.9% (299/315, D1+D2) are therefore RETIRED.** They
> stay below as the dated record of what was measured on 2026-08-03, which is all
> they ever were. Do not quote either as a current state of coverage.
>
> **The current figures — never one without its scope.** Both printed by
> `python tools\uimap\coverage_rederive.py`, the only tool permitted to state a
> coverage figure, run 2026-09-01: **90/90 = 100.0% *of RETAIL-REACHABLE stock
> .UI roots*** (117 total − 27 the retail game cannot instantiate), and
> **93/117 = 79.5%** over ALL roots, kept so the 27 exclusions stay auditable.
> **"100% of the UI" is FALSE and must never be written here** — the unbounded
> code-created channel (§0.1) sits outside every denominator on this page.
>
> Distinct-id is the strictest because many roots share an id: covering one
> instance of an id does not cover the id. It is the number that cannot flatter
> us, which is precisely why it was chosen.
>
> **Also corrected by measurement** — §2 below says 22 multi-root scripts / 49
> extra roots; the instrument measures **21 / 48**, and the headline ladder
> `339/282/330/329/117` is stale (`330 → 338` depth-0 roots). The instrument now
> prints this disagreement on every run rather than letting the doc drift.
>
> Everything from here down is kept as the historical record of how the number
> moved. Read this box first, and take any figure below as scoped, not headline.

> ## ⚠ AMENDED 2026-08-03 (later the same day) — READ §0 FIRST
>
> The code-created-window census landed, four adjudications landed, and a
> refutation pass broke three claims in this file. **The headline moved from
> 96.6% to 94.9%, §5's PROVEN-UNREACHABLE table is now WRONG in two of its
> three rows, and `0x6A5E44B6`'s "IDENTITY UNKNOWN" was already stale when it
> was written.** §0 below carries the corrections; the full reasoning, the
> per-root cure briefs and the batched eyes-on runsheet are in
> **`tools\research\FINAL-3-PERCENT.md`**.

Every number below was produced by a run recorded in "How to reproduce" at the
bottom. Where the three inventories disagreed, the disagreement is named and
resolved with evidence — not averaged.

---

## 0. AMENDMENT 2026-08-03 — the code-created denominator

### 0.1 The headline falls to 94.9%

> ### **94.9% — 299 of 315 named shipping windows carry a scaling mechanism.**
> (was 96.6% = 288/298, which counted only the *scriptable* UI)

Three denominators. **Never merge them.**

```
D1  script-declared shipping ROOTS         298     covered 288    96.6%   (unchanged, correct for its scope)
D2  code-created NAMED shipping windows     17     covered  11    64.7%   (NEW)
    -------------------------------------------------------------------
    D1 + D2   (the honest headline)        315     covered 299    94.9%

D3  windows we can SEE but cannot NAME     — not a percentage; see §0.4 —
```

**The bound, stated as a bound: at least 315 named shipping windows exist, and
there is no offline upper bound.** Three channels put windows outside the census
by construction, all measured 2026-08-03 from `tools\uimap\_work\edges.json`:

1. **A third creation route the census does not model** — creation through the
   runtime COM singleton `0xC2C2EB0F` (getter `sub_913C72` @ `0x00913C72`): no
   literal clsid, no `call 0x005E55E0`, invisible to Route A *and* Route B.
   **220 call sites in 129 functions; 106 of the 129 the census sees as no kind
   of creator; 27 of those 106 are in the live-UI band `0x760000–0x7FFFFF`.**
2. **Ids passed in a register.** 162 `call [reg+0x100]` sites exist; the literal
   scan matches 73. **89 (55%) pass a non-literal argument.** Concrete case:
   `sub_779660` (86 call sites in 6 functions, `push edi; call [edx+0x100]`)
   creates `0x0ABCE000`/`0x0ABCE001`/`0x0ABCDE00-02` — on screen, patched by us
   in `CodePatches.cpp:246`, in **neither** denominator. Same defect stamps
   `0x42B7C353/54/55` inside `sub_99A70F` — 3 of the scrollbar's 4 ids invisible.
3. **109 anonymous creation sites** (24 in the live-UI band) — windows never
   given an id at all.

### 0.2 D2 in full — the 17 named code-created shipping windows

| id | what | verdict | mechanism / why not |
|---|---|---|---|
| `0x9A47B417` | `cSC4View3DWin` | COVERED | sweep root, must stay full-screen |
| `0x6104489A` | SC4 App window | COVERED | sweep root, must stay full-screen |
| `0x6A5E44B6` | **`cSC4WinAlertBorder`** | COVERED | art (3 sheets) + ≥90% skip at `UiSpike.cpp:7630`; #59 user-confirmed |
| `0x2AAB8CC1` | tooltip layer | COVERED | wrap patch + art, #41 |
| `0x8A6E61E0` / `0x8A2CAD8B` | sub-flyout containers | COVERED | born-scale, #76/#95 user-confirmed |
| `0x2BA6BB97` | `cSC4WinRegionView` | **COVERED — was "PROVEN UNREACHABLE"** | dialog-static on both bubble scripts; #72 user-confirmed. §0.3 |
| `0x0423278D/E/F` | Ordinances / shared text popup | **COVERED — was "no mechanism"** | `CodePatches.cpp:201/246/256/464` + `UiSpike.cpp:11769`, `:11816-11945`, `:11900`, `:12008-12060` |
| `0x4C30E4FA` | ×6 pooled **My Sims world-anchored callout** | COVERED **but AT-RISK** | in `kCityDialogIds` (`:11207`) — but the label "Business Deals empty-state box" is **unsupported** (creator is `sub_42C0E0` My Sims; `ShowWindow` at `0x00431130`) and two levers fight |
| `0x00000043` | Restore-Toolbars button | **UNCOVERED — quantified defect** | **10 px clip at birth, 20 px after our own sweep** (2x art `42x38` at the code-fixed `(12, viewH−28)`) |
| `0xEA659793` | region screen | UNCOVERED | region pass is whitelist-only |
| `0x6A0AF41D` | region **cloud particle emitter** | UNCOVERED — correctly | sprite size is the code constant `float @0xAB7E10 = 128.0`; cosmetic; **leave alone** |
| `0x85202C0E

> ⛔ **CORRECTED 2026-09-01 — ALL THREE CLAIMS IN THIS ROW-SET ARE WRONG.**
> The three windows were called "the only genuine D2 work left" and
> "player-reachable through Photo Album and recorded animations". Measured:
>
> * **`0x85202C0E` is not an export-resolution preset picker.** It is the
>   **SNAPSHOT / CAMERA MODE capture frame**, opened by the camera button
>   `0x8A1DA655` on the city dock and by the command the game's own registry
>   names `kCommandID_OpenSnapshotDialog` (`0x6A935E4B`). Its own LTEXTs read
>   "Click or press enter to take snapshot", "Press escape to cancel",
>   "Press the spacebar to change size".
> * **Its vtable is `0x00AB9BF8`, not `0xAB9980`.** The ctor stamps AB9BF8 at
>   `0x7B748B` and the live log prints `vt=00AB9BF8`.
> * **"Never in any retained log" is false.** It is in
>   `_tests/captures/SC4UIScale-2026-08-19-121243.log:8829` —
>   `VWKID 0 id=0x85202C0E vt=00AB9BF8 (0,0 2400x1600)` — and five seconds
>   later the Photo Album root opens from the button beside it.
> * **SCALING IT WOULD BE THE DEFECT.** Its width and height ARE the export
>   resolution in real pixels. It is now in `kNeverScaleIds` so the exclusion
>   is enforced rather than an accident of the full-screen default.
> * **`0x9AEDEF7C` is DEV-ONLY.** No player gesture reaches it, and its modal
>   chain is SHARED with a working dialog — so acting on this row would most
>   likely have broken something that works.
> * **`0xA802B4EB` was ALREADY COVERED** by host/child geometry, no code
>   needed. Graded COVERED — STRUCTURAL, UNOBSERVED.
>
> **D2 tops out at 15/16 = 93.8%, not 100%**: `0x6A0AF41D` is a deliberate
> leave-alone whose sprite size is the code constant at `0xAB7E10` = 128.0,
> so there is nothing to cover and nothing to exclude.
`, `0xA802B4EB`, `0x9AEDEF7C` | ? | ROLE UNKNOWN | never in any retained log |

### 0.3 §5's PROVEN-UNREACHABLE table is WRONG in two of three rows

- **`0x2BA6BB97` — REFUTED BY MEASUREMENT.** In
  `_checkpoints\pds-cache\SC4UIScale-snapshot.log`, three dumps read
  `children=0` and the **fourth (`:151-165`) prints 13 descendants**: the
  city-select bubble `0x0A551C50 (1049,456 516x500)` and its 12 children.
  `children=0` is a **state-dependent measured null** meaning "no bubble open" —
  the PRE-FOUNDING failure mode our standing order names. Worse, we had
  **already shipped a user-confirmed fix into this subtree** (#72,
  `REGRESSION.md:3531`), and every live rect under it is exactly 2x its staged
  script. The subtree is not merely reachable — it is already fully scaled.
- **`0x6A5E44B6` — identity was never unknown.** It is `cSC4WinAlertBorder`,
  clsid `0xCA5D3294`, vt `0x00AB5B48`, id set at `0x007EF072`, drawn by
  `Plot = 0x00794100` (one nine-slice, `cell = img/3`, corners unstretched).
  Named, fixed and user-confirmed **2026-07-31 as #59, v2.37.2** — three days
  before this file called it UNKNOWN.
- **City LOADING / SAVING** — this row still stands. No `.UI` exists anywhere in
  the corpus and it never appears in the tree.

**Instrument lesson, now a law:** `RGKID`'s printer is depth-capped at 4 levels
and skips invisible children. A **visible** window at level 5
(`cSC4WinAuraBar 0x4A553000`, declared 102x11 in `I-ca539340`) was ruled "NOT A
WINDOW / code-painted" by `task55-47-runtimeimg.md:1455`. **A saturated
enumerator manufactured an unreachability verdict.** Any future "code-painted"
verdict must state the enumerator's depth cap and visibility gate.

### 0.4 D3 — the 36 "unexplained" live ids collapse to ONE family

**171** distinct window ids appear across the 5 retained logs. **122** are in the
`.UI` corpus, **12** are in the census's 64 literal-`SetID` ids, and **36 are in
neither.** That looked like a 21%-of-live denominator hole.

**It is not. Every one of the 36 resolves to the Ordinances family:**

```
0x0000012C..0x137 (12)  0x000002F4..0x2FF (12)  0x00000551..0x554 (4)
0x0000016D, 0x000001CD           ── all children of 0x0423278F  (MWKID)
0x0ABCE000, 0x0ABCE001           ── children of 0x0423278F      (POPKID)
0x00000168/0x68, 0x00000484/0x384 ── the ordinance popup dump    (POPKID)
```

They add **zero roots** to any denominator (they are children, not roots) and
their coverage is inherited from `0x0423278F`, which is covered. **One already
known, already covered family — not 36 gaps.**

### 0.5 What the residual actually is — the useful finding

> ~~**The sweep is structural, not id-keyed.** `ScaleSubtree` recurses on the child
> list. A window does not need an id, a script, or a list entry to be scaled — it
> needs a **covered ancestor**.~~
>
> **⚠ CORRECTED 2026-08-16 — a covered ancestor is neither SUFFICIENT for the
> runtime sweep to reach a window, nor NECESSARY for that window to end up
> scaled.** The recursion is structural only until an **id-keyed EARLY RETURN**
> stops it, and there are **four**, not one. `ScalePanelRoot` scales the root and
> then returns for every id in `kDataScaledSubtreeIds` **before** its child loop
> (`UiSpike.cpp:14570-14573`; loop at `:14579`). `ScaleSubtree` returns before
> its own child loop (`:17417`) three separate ways: `kAdviceListNeverTouchIds`
> (`:17175-17178`), `kFontSizedIds` (`:17358-17372` — position moved, children
> never walked) and `kAdviceListScaleSelfIds` (`:17412-17415` — self scaled,
> children never walked). Two non-id caps stop it as well: `kMaxDepth = 8` and
> `kMaxWindows = 1500` (`:4721-4722`, tested at `:17153`, now logged at `:17137`
> / `:17148`).
>
> **`0x6A15C767` — the Advisors console strip — is the FIRST entry in
> `kDataScaledSubtreeIds` (`UiSpike.cpp:5374`), and it is a DIRECT view child**,
> so it is swept as a panel root (`ScalePanelsUnder` enumerates direct children
> only, `:10185`; `ScalePanelRoot` at `:10320`) and the data-scaled return fires
> before the child loop. **The runtime sweep therefore NEVER walks its seven face
> buttons.** The log says it in one line — `city panel 0x6A15C767 - 1 windows
> scaled` (`_tests\REGRESSION.md:10255`): one window mutated, the root. A runtime
> rule keyed on a button class cannot reach those leaves, which is why #167's
> `stripBtnClass` was dead code here (`_tests\REGRESSION.md:10252`).
>
> **And "data-scaled" means TWO files, not one.** The button WINDOW ships from
> `tools\selective-safe\build_selective_safe.py` (`double_subtree_areas`,
> `:1963`) — that half was #170. The ART CELL the window must match ships from
> the upscaler's `ScaleDim` / `CellUnit` — that half is **#171, still open** (132
> pre-scaled buttons whose cell is over-snapped at 1.5x; 0 at 2x/3x). Reaching
> for the builder *alone* is the next version of this same mistake.
>
> What survives of the original claim, and only this: a window inside a subtree
> that is **actually** recursed needs no `id=`, script or list entry of its own —
> which is why `0xAA5C2F86` and `0xC7A0E17E` scale today (see below).

Proof, and it closes three "UNIDENTIFIED" entries in §8: `0xAA5C2F86` (TrendBar,
145x9) and `0xC7A0E17E` (status-panel meters, 71x4 / 8x71) appear in the corpus
**only as `clsid=`, on nodes carrying no `id=` at all** — and they are scaled
today purely because their parent root is swept. And **`0x28C5A41F` is not a
window id at all**: it is the `clsid` of the Data Views **Map-View page**, which
in all three declaring scripts (`I-0b72f276`, `I-2bc9060f`, `I-ea287193`) carries
`iid=IGZWinCustom id=0x00004200` — the page that hosts scrollbar `0x42B7C351`.

So: **the named residual is 16 windows**, each with a next step. **The unnamed
residual is large in count and low in risk**, being overwhelmingly anonymous
children inside covered parents. **The part that should worry us is neither** —
it is the 27 live-UI-band call sites into a factory no offline tool here can
enumerate (§0.1 item 1).

### 0.6 A denominator gap independent of the code-created one

The ladder counts **depth-0 roots**. But the loader's window-id argument selects
**any node** in the deserialized tree, not the root: at `0x007EEB05` the code
loads script `0x2bc9060f` and asks for **`0x00004200`, a depth-1 child**
(`area=(246,-320,519,-143)`). Positive control: the same depth-tracked scan
returns depth 0 for six other script→winId pairs. Also: `I-6a9455c9` has **two**
depth-0 roots (`0x27df05bf` and `0x27df05be`, both 46x97), so "the root" is
undefined for that script.

**Ladder re-run over all depths — 2026-08-23, `tools\uimap\depth_ladder.py`.**
Same corpus (339 files), same tag grammar and latin-1 decode as
`coverage_rederive.py`; depth accounting balanced (`final_depth==0`,
`min_depth==0`) on every file. Result:

| depth | id-bearing nodes |
|---|---|
| 0 (the census denominator) | 337 |
| 1 | 2010 |
| 2 | 1324 |
| 3 | 641 |
| 4 | 5 |

**1,296 distinct ids exist at depth ≥1 somewhere in the corpus** (3,980
id-bearing occurrences) — that is the full candidate set of nodes a loader
call could in principle address as a non-root winId, the way `0x00004200` is
proven to be. `0x00004200` itself reproduces at **depth 1** in all three
declaring scripts (`I-0b72f276`, `I-2bc9060f`, `I-ea287193`,
`area=(246,-320,519,-143)`), matching the prior measurement exactly.

**This closes the corpus-side half only.** Cross-checked against the 7
script→winId pairs FINAL-3-PERCENT.md §4.0(b) pulled from disassembly, all 7
reproduce their documented depth (6 at depth 0, 1 — `0x00004200` — at depth 1).
That 7-pair set remains the **entire measured universe of code loader call
sites** in the repo; it is not an exhaustive sweep of `.text`, so "1 of 7 is
depth-1+" is not a rate that generalises. **The code-side count — how many
loader call sites in the compiled binary actually target one of the 1,296
depth≥1 candidate ids — is still open** and requires enumerating every caller
of the winId-loader thunk family (`sub_5F9480`-style, per §4.0(b)) across
`.text`, e.g. via `funcs.json`'s caller-count table plus a disassembler
reading each call's pushed winId argument — not derivable from the `.UI`
corpus alone.

### 0.7 Two data gaps found in passing

- ~~**`kCityDialogIds` `0xAA921F4F` is missing a fourth measured base.**~~
  **✅ CLOSED 2026-08-16 — shipped in v2.64.0 (#102); verified against current
  source.** The struct is `int32_t bw[4]; int32_t bh[4]; };`
  (`UiSpike.cpp:14713`) and the table row already carries the fourth base:
  `{ 0xAA921F4F, 330, { 330, 270, 270, 330 }, { 157, 161, 162, 109 } }`
  (`UiSpike.cpp:14775`). The widening is recorded in-place at
  `UiSpike.cpp:14707` ("v2.64.0 (#102): widened 3 -> 4"), `:14746`
  ("bw[]/bh[] widened 3 -> 4, 330x109 added, loop bound now") and `:14767`.
  The exact-product loop no longer carries a literal bound — it reads
  `static_cast<int>(sizeof(dlg.bw) / sizeof(dlg.bw[0]))` (`UiSpike.cpp:15064`),
  with its own note that "the 3 that used to sit here is exactly how the 4th
  base went unread" — so a future widening cannot leave the loop behind.
  ⚠ Also stale in the struck text: the pointer `UiSpike.cpp:11172` is dead;
  that line now sits inside the Graphs chart-geometry block. Nothing to do here.
  ⚠ NOT VERIFIED: the closure is asserted from the source and from the in-file
  v2.64.0 comments only — there is no CHANGELOG.md in the project root, so the
  "v2.64.0" label is taken from the code comments themselves. The
  LATENT-not-live statement in the surviving text below still matches
  `UiSpike.cpp:14755` and needs no change.
  `UiSpike.cpp:11172` holds bases `{330x157, 270x161, 270x162}` in a `bw[3]/bh[3]`
  struct, but **three** stock scripts declare that id: `I-0a55161d` 330x157,
  `I-6a553aa4` 270x161, and **`I-4a551b4c` 330x109** (region-screen Quit confirm,
  staged at all three tiers: 660x218 / 495x164 / 990x327). No listed base
  produces those, so the exact-product guard would set `dataBorn=false` and
  re-scale 660x218 → **1320x436** — the v2.39.14 shape. **LATENT, not live**
  (`Disarm()` on `kSC4MessagePreCityShutdown` stops the pass with no city
  loaded). ~~Widen to `bw[4]/bh[4]` and add `330x109`.~~
  **Done in v2.64.0 (#102) — see the CLOSED note above (`UiSpike.cpp:14713`,
  `:14775`, `:15064`), 2026-08-16.**
- **`0x4C30E4FA`'s label** must be re-derived before anything keys off it (§0.2).

### 0.8 Collisions are the MODE, not an accident

`tools\uimap\idcollide.py` (new) → `_work\idcollide-report.txt`: **596 of 1409
distinct corpus ids (42%) are declared by ≥2 different script instances**, and
**64 of our own 174 id-keyed entries (37%) are multi-declared**
(`kDataScaledSubtreeIds` 9/10, `kAlwaysScaleCityIds` 16/33,
`SCALED_WINDOW_IDS` 20/51). **Every id-keyed rule we ship is already a
multi-window rule.** The discriminator that works, with four shipping
precedents: apply a cure to the pair *(builder, script-instance TGI)*, never to
*(any builder, window id)* — unless the list is provably inert for every window
answering that id. `kNeverScaleIds` is inert for main-window children and is
therefore the one id-keyed list where a collision is harmless.

**⚠ Corollary:** `kBmpxDialogRoots` (`UiSpike.cpp:12182`) resolves with a
**single first-match walk** (`:7015`) and its tracker is keyed by id. **Never add
a known-colliding id to it** — it returns an arbitrary instance and the
`BMPX draw-skip … win WxH` line then reports the wrong window's frame.

### 0.9 ⚠ Every line number in the pre-amendment reports is stale

Task #57 (v2.55.0) edited `UiSpike.cpp` on 2026-08-03 *after* those reports were
written. Verified drift: `7609→7630` (≥90% sweep guard), `12549→12587`,
`12144→12182` (`kBmpxDialogRoots`), `3184→3117` (`kNeverScaleIds`),
`3165→3186` (`0x4A35B0F2`), `7010→7015`, `11150→11172`. **Match on text, never on
line number.**

### 0.10 `0x6BB92BCB` (#98) — ROLE CORRECTED; cure BUILT, then MEASURED ABSENT

Two separate things happened to this row on 2026-08-03. **They must not be
merged**: one is settled, the other is not.

#### (a) SETTLED — the census's ROLE for this id was wrong

`0x6BB92BCB` is **not a live root**. It is a **CONSTRUCTION-ONLY CONTAINER**.
Measured from the exe, not inferred: its id occurs exactly **ONCE image-wide**
(VA `0x004C594F`; created at `0x004C595C` from TGI
`{0,0x96a006b0,0xabb0120f}`) and `0x218` bytes later the **SAME** function calls
`mainWindow->ChildDelete(container)` at `0x004C5B64` (`cIGZWin` vt+0x40). It
never lives in the window tree, so **its `area=` is DEAD DATA** — the "1x root
box" §4 reports is a **PHANTOM**, and no amount of scaling it can move a pixel.
It is scaled only so the file stays internally consistent.

The two **REAL** windows are its children, **PROMOTED to direct children of the
MAIN WINDOW**: `GetChildAs(0x0BB0F5E7)` -> `ChildRemove` -> `ChildAdd`
(`0x004C5A04..0x004C5A16`), and the same for `0x6BB92BCA`
(`0x004C5AB5..0x004C5AC8`). **No sweep root reaches a main-window child** — city
is `SC4View3DWin`, region is `0xEA659793`, and neither id is in
`kCityDialogIds`. That is precisely why the 2x art we had **already shipped**
was drawing out of **1x** windows.

The script also carries **14** distinct art refs, not the **12** §4 quotes: 13
EXCLUSIVE/2x-in-place plus one SHARED (`0x14416245` -> clone `0x47026244`).

> ⛔ **Do NOT add `0x0BB0F5E7` or `0x6BB92BCA` to any CITY runtime list.** Both
> are **ALREADY in `kRegionPanelIds`**, and the REGION legend is a **DIFFERENT**
> script (`I-abc0ed33`). A city-side entry stacked on that is **4x**. This is
> the §0.8 collision law biting on a specific pair of ids.

#### (b) NOT SETTLED — the cure was built and deployed, and is not on disk now

A data-only cure was written into `tools\selective-safe\build_selective_safe.py`
(`double_one_window_area` + `double_subtree_areas` on `6bb92bcb`, 1 root + 36
descendants, followed by an in-generator **ADJUDICATOR** that `sys.exit()`s
unless all 9 `GZWinBMP` satisfy `area == imagerect`, row pitch >= art height and
drawn right edge < label column). It was **deployed 12:39:39** with
`Test-DatIntegrity` ALL PASS. Full description, scope and failure modes:
**`_tests\REGRESSION.md` → *IN-GENERATOR ADJUDICATOR (#98)***.

**MEASURED 12:44-12:53 the same day, and it contradicts that record:**

| probe | result |
|---|---|
| `abb0120f` in `build_selective_safe.py` (mtime **12:44:10**) | **0 hits** |
| `6bb92bcb` / `TRIP TYPES` in the same file | **0 hits** |
| `stage\`, `stage-15x\`, `stage-3x\` — root `0x6bb92bcb` | `area=(139,81,320,377)` — **1x at all three tiers** |
| the 9 `GZWinBMP` icons, all three tiers | `area=(48,43,66,57)` = **18x14**; `imagerect` 36x28 / 27x21 / 54x42 |

The last row **is the defect**, still present at every tier: row pitch 21
against art height 28 (7 px of vertical overlap per row) and a drawn right edge
of 48+36 = 84 against the label column at x=71 (13 px into the label text).

**POSITIVE CONTROL** (this file's own standing order — a null is not evidence
until you prove the probe could have seen the thing): the identical grep, run
minutes earlier in the same session against the same path, returned the whole
block verbatim at lines 1288-1379. The probe sees the block when the block is
there. This is a **MEASURED absence, not a structural one.**

Supporting: the deployed `SelectiveArt-2x` was **rebuilt at 12:44**
(11,712,063 bytes vs 11,712,095 at 12:37 — so the 12:39 package was
*overwritten*, not merely disabled), and every package in `Plugins\` is
currently renamed `.compare-off` / `.x1-disabled`, i.e. the folder is in
**stock-compare** state.

> ⚠ **The stock-compare half of that sentence expired at 13:10 (re-measured
> 13:14).** Zero `.compare-off` files remain and the game ran at 13:10:19 on
> v2.55.0 at **tier 1.50** (1400x1050). The surviving `.x1-disabled` files are
> just the **inactive tiers**, which is normal shipping state, not
> stock-compare. **The rebuilt-at-12:44 half still stands**, and the #98 cure is
> still absent — re-confirmed a third time at 13:14 with its positive control.

**Cause: NOT ESTABLISHED.** A concurrent session, an editor flushing a stale
buffer, and a OneDrive sync-down all fit what was measured, and nothing here
distinguishes them. **No cause is written down until one is measured.**

**RE-CONFIRMED 12:58-13:00 by an independent run.** A later session was briefed
that the cure was present and deployed; it ran the four probes before editing
this file. All four reproduced unchanged — 0 hits in the generator (mtime still
`12:44:10`, 86,195 bytes), and `area=(139,81,320,377)` / `area=(48,43,66,57)` at
all three tiers. Positive control for *that* run: the same grep printed 29 hits
for `double_one_window_area`/`double_subtree_areas` with line numbers, and their
five actual call sites are `6a15c767`, the budget roots, the graph roots,
`4bcb938a`, `ec1a5cbf` — **none is `6bb92bcb`**. This **rules out a transient**
(an unflushed buffer or an in-flight sync should have resolved inside 16
minutes) but **still does not establish a cause**, so none is written.

#### What this does to the numbers — both readings, and the one that is true today

`0x6BB92BCB` is currently counted **UNCOVERED**: it is item **1** of §4's 10
root slots / 9 distinct ids. Flipping it would give:

```
D1     covered 288 -> 289  of 298     96.6% -> 97.0%   (289/298 = 0.96979)
       uncovered  10 ->   9 root slots,   9 ->  8 distinct ids
D1+D2  covered 299 -> 300  of 315     94.9% -> 95.2%   (300/315 = 0.95238)
```

> **The headline is NOT moved, and the reason is a measurement rather than
> caution: as of 12:53 the cure is in neither the generator nor any staged
> tier, so nothing on disk supports 97.0% / 95.2%. This file continues to read
> 94.9% (299/315).**

~~Re-run the two probes in (b). **If and only if** they come back non-zero and
2x, apply the arithmetic block above verbatim, date it, and strike §4 row 1.~~

**⛔ VOID 2026-08-16 — DO NOT EXECUTE THIS INSTRUCTION.** The probes' zero result
is the correct shipping state, so the condition can only be met by someone
re-introducing the regression. #98 is CLOSED NOT-A-BUG, user-confirmed on screen;
the arithmetic block stays unapplied and §4 row 1's count is unaffected.
`VERSION-HISTORY.txt:3322-3342`, `:2647-2652`.

⚠ **And price the flip before you make it, because it WIDENS the definition**
(law: *an offline gate is only as honest as its scope* — the same law §1 and §9
already invoke about the 8 third-party exclusions). §1 defines "covered" as
*id named in `src\UiSpike.cpp`* **OR** *script staged by `tools\dialog-static\`*.
The #98 cure is **neither**: it is `tools\selective-safe\` data-doubling with
**no runtime half at all**, and it would be the **first** root counted as
covered by that path alone. Counting it grows the definition a **third arm**.
That is defensible — the mechanism is real and it is gated — but it is a change
in what the numerator MEANS, and it belongs beside the number, not under it.

**Eyes-on state, unchanged either way: DEPLOYED, NOT USER-CONFIRMED.** No one
has opened Route Query since the build. Every figure above is a generator or
file measurement; nothing has looked at a pixel.

---

## 1. The headline, stated honestly

> **96.6% — 288 of 298 script-declared shipping roots carry a scaling mechanism.**
>
> **⚠ SUPERSEDED as the headline — see §0.1. This figure is still correct for its
> stated scope (script-declared roots) and is retained as D1.**

That sentence is only meaningful with all three of these attached:

1. **"Covered" means MECHANISM-PRESENT, not VERIFIED-CORRECT.** A root counts as
   covered if its id is named in `src\UiSpike.cpp` (runtime path) **or** its
   script is staged by `tools\dialog-static\` (static path). Neither test looks
   at a pixel. `0x6BB92BCB` was "covered" by the old text sweep and is a live
   defect (§4). *(Its ROLE was also wrong: it is a construction-only
   container whose `area=` is dead data, not a live root — §0.10.)*
2. **"Script-declared" excludes code-created windows entirely.** The denominator
   is built from the 339-file `.UI` corpus. Windows the game constructs in code
   — the region map, the loading screen, the full-screen view layers — are **not
   in it at all** (§5). The 96.6% is a percentage of the *scriptable* UI, which
   is smaller than "the UI".
3. **Only 60.9% of distinct shipping root ids have ever been observed live**
   (56 of 92). Coverage is an offline claim; the live corpus is far thinner (§6).

### Why this is 96.6% and the old doc said 94.7%

The old **numerator reproduces exactly: 288.** Only the denominator moved.

| | old (2026-07-29) | now (2026-08-03) |
|---|---|---|
| denominator | 304 | **298** |
| built as | 329 roots − 25 dev-editor | 330 roots − 24 dev-editor − **8 third-party plugin** |
| covered | 288 | 288 |
| uncovered | 16 | **10** |
| ratio | 94.7% | **96.6%** |

The number went **up**, and it is important to say why, because "coverage rose"
is the kind of claim that should be distrusted by default:

- **6 of the old 16 uncovered roots were genuinely fixed** between 07-29 and
  today (bucket D items 1, 3, 4, 5, 9 — verified present in current source at
  `UiSpike.cpp:3174,3177,3178` and `build_dialog_static.py:352-354`). That is a
  real improvement, not a redefinition.
- **8 third-party plugin roots left the denominator.** This is a *new* exclusion
  and it flatters the number by ~0.2pp. It is defensible — they are other
  people's mod UI, not SimCity 4's — but it is a narrowing and is flagged here
  rather than buried (law: *an offline gate is only as honest as its scope*).

**The old 94.7% was not inflated. It was correct for its date.** No hard case
was quietly dropped from the old denominator; the 25 dev-editor exclusions were
disclosed then and are still disclosed now.

### The number that is NOT good news

Against the live corpus rather than the offline model:

> **60.9% (56 of 92) of distinct shipping root ids have ever appeared in any
> retained log.** 28 covered ids have never been seen live even once.

That is the honest measure of what we have *watched work*, and it is 36 points
below the mechanism-coverage figure.

---

## 2. Denominator ladder (each exclusion is explicit and auditable)

```
  all depth-0 <LEGACY> roots in the .UI corpus   330
  − third-party PLUGIN roots                      -8
  − dev-editor roots (each caption-verified)     -24
  = SHIPPING GAME roots        [denominator]     298
      covered (runtime list OR static-doubled)   288   96.6%
      uncovered                                   10    3.4%
```

Corpus shape, ~~independently recounted today and **confirming the old doc**:
339 `.ui` files on disk → **282 layout scripts** (banner-matched) → **330**
depth-0 roots, of which **329** carry a nonzero `id=` and one is id-less →
**116** distinct nonzero root ids (**117** counting the id-less root).~~

**⛔ CORRECTED 2026-08-16 — that ladder is the PRE-#99 (buggy) corpus, and the
recount that "confirmed" it was not independent.** The header box at :39-45
already flags `339/282/330/329/117` as stale; this is the in-place fix it never
made. Measured:

339 `.ui` files → **290 layout scripts** → **338** depth-0 roots, of which
**337** carry a nonzero `id=` and one is id-less → **117** distinct nonzero root
ids (**118** counting the id-less bucket). Source `coverage_rederive.py:195-208`
(`EXPECT`); the 2026-08-16 run printed all **ten** `EXPECT` assertions `[OK]`,
including `depth-0 roots expected 338 measured 338` and `distinct nonzero root
ids expected 117 measured 117`.

The instrument deliberately keeps this section's exact tuple as
`EXPECT_BEFORE_CORPUS_FIX` — `282 / 330 / 329 / 116 nonzero`
(`coverage_rederive.py:214-220`) — because, per the comment at
`coverage_rederive.py:211-213`, it is *"kept so the size and DIRECTION of the
instrument's error stays on the record"*. `coverage_rederive.py:870-892` prints
the disagreement against **this section by name** on every run.

**Why the recount agreed, and why that agreement was worth nothing.** The corpus
did not change. Replaying the pre-#99 filter — exact string
`"# Generated by UI editor"` after a plain `str.lstrip()` — over *today's*
corpus still yields exactly `282 / 330 / 329 / 116`. `scratchpad\recount.py`
used that same filter, so it inherited the same blind spot: **two blind
instruments agreeing is one instrument.** It dropped 8 real layout scripts by
two mechanisms (`coverage_rederive.py:73-82`):

- 1 game script, `extracted\T-00000000_G-96a006b0_I-ca551016.ui`, whose first
  bytes are `EF BB BF` *before* the exact banner — `lstrip()` strips whitespace,
  not a BOM. Root `0x0A592004`.
- 7 plugin scripts banner-stamped `# Generated by UIEditor - Reader 1.0.0`
  ("UIEditor", not "UI editor"; `startswith` is case-sensitive and exact).

Positive control for the exclusion: **all 290** files the corrected filter
accepts contain the bytes `<LEGACY`, and **all 49** it rejects contain **zero**.
The 8 recovered files are therefore demonstrably layout scripts, not junk a
looser filter let in. §3.2's "**330 / 329 / 117. The old doc's numbers are
correct**" (:457-458) is wrong for the same reason and needs the same strike.

⚠ The denominator ladder above (`330 − 8 − 24 = 298`) starts from the same
stale 330 and must be re-derived before it is quoted — but **not** as
`338 − 8 − 24`. The 8 recovered roots split **7 third-party plugin + 1 SHIPPING
GAME root** (`0x0A592004`), so the `− third-party PLUGIN roots` line moves as
well as the total. Re-derive both, do not subtract the old constants from a new
total.

Of the 288 covered: **133** runtime-only, **87** static-only, **68** both.

~~**22 scripts contain more than one top-level root** (49 extra roots beyond the
one-root-per-file assumption).~~ This matters — see the `coverage_rederive.py`
defect in §3.

**⛔ CORRECTED 2026-08-16 — measured 21 / 48**, and this one is *not* a side
effect of the corpus fix: 21 / 48 is what the pre-#99 **and** the corrected
corpora both measure, because all 8 recovered scripts are single-root.
Arithmetic: `338 roots − 290 layout scripts = 48`; 49 is only reachable if some
layout script declares **zero** top-level roots, and measured zero-root scripts
= **0** (`coverage_rederive.py:877-881`).

---

## 3. Reconciling the three inventories

### 3.1 Where is `coverage-matrix.md`? — live-evidence was right

The roots and crosscheck inventories both wrote `tools\uimap\coverage-matrix.md`.
That file **did not exist**. The real document was
`tools\research\_checkpoints\coverage-matrix.md`. Resolved by `ls`. This file now
occupies the `tools\uimap\` path the workflow expects.

### 3.2 Are 329 / 117 reproducible? — BOTH inventories were wrong, in opposite directions

- **roots** claimed "✅ exact", credited to `coverage_rederive.py`.
- **live-evidence** declined to verify, calling the script mid-edit.

I counted independently (`scratchpad\recount.py`, depth tracked through
`<CHILDREN>`/`</CHILDREN>`): ~~**330 / 329 / 117. The old doc's numbers are
correct.**~~

**⛔ CORRECTED 2026-08-16 — same defect as §2, and the same strike.** That
recount was **not** independent: it reused the pre-#99 banner filter (exact
`"# Generated by UI editor"` after a plain `str.lstrip()`), so it inherited the
same blind spot and dropped the same 8 layout scripts. Measured today:
**338 / 337 / 117 distinct nonzero**. See the 2026-08-16 correction in §2 for
the mechanism, the two drop causes and the `<LEGACY` positive control.

But `coverage_rederive.py` **does not produce them**, and cannot. Its
Section 2 prints `282 roots / 281 with id / 91 distinct` because
`parse_script()` `break`s at the **first** `<LEGACY>` in each file:

```python
for ln in lines:
    if RE_LEGACY.search(ln):
        ...
        break          # <-- one root per file
```

So it silently drops the **49 extra top-level roots** in those 22 multi-root
scripts. Consequences:

- Its headline "✅ exact" agreement was **never actually tested by the tool**.
- **Its Section 5 coverage ratio (241/281 = 85.8%) has the wrong denominator**
  for its stated purpose and should not be quoted. The roots inventory quoted it
  as an independent measure; it is not comparable to 96.6% (different
  denominator, and it ignores dialog-static coverage entirely).

*This is exactly the failure the law warns about: an inference written down as a
measurement. The tool was believed because it printed a number.*

### 3.3 Is crosscheck green? — not a contradiction, a clock difference

live-evidence measured **exit 1 / 12 MISSES**; roots and crosscheck reported
**green**. Both are true: `builders.json` and `constants.json` were rewritten at
**09:43:44** today, between the two observations. Verified green myself at
09:47 (§7).

### 3.4 What are `0x0A41C7B2` / `0x0A41C7B3`? — three sources, one reconciliation

Three claims existed, and I could check the strongest one:

| source | claim |
|---|---|
| old `coverage-matrix.md:28` | "Establish/Obliterate neighborhood" |
| `MAYOR-MODE.md:825` | "Disaster" |
| roots inventory | tutorial pointer arrows; "both prior notes wrong" |

**MEASURED (exe, `1189720d5e15b0e1`, 7876608 bytes):** the roots inventory's
disassembly is correct and I reproduced it. The range `0x443E60–0x444160` is
**one function** (single `ret`, at `0x444152`) and it loads all three scripts:

```
0x443e70  mov dword ptr [esp+0x14], 0x96a006b0
0x443e78  mov dword ptr [esp+0x18], 0xa2dd355   ; tutorial page ("Continue"/"Exit Tutorial")
0x444057  push 0xa41c7b2 / 0x44405c  push 0xa41be3e
0x44407e  push 0xa41c7b3 / 0x444083  push 0xa41be3f
```

**ALSO MEASURED (the script itself):** the single button inside `0x0A41C7B2`
carries `tiptext="Disaster Tools"`.

**Resolution — both measurements are right.** These are **tutorial pointer
overlays that highlight the Disaster Tools button**, inheriting that button's
tooltip so hovering still reads correctly. That single reading satisfies the
code evidence *and* the data evidence. Scoring the three prior claims: the old
`coverage-matrix.md` entry is simply **wrong**; `MAYOR-MODE.md` was right about
the *subject*; roots was right about the *owner* but overreached in declaring
both prior notes wrong.

- Owner = tutorial builder — **MEASURED**.
- "Arrow"-shaped art — **INFERENCE** (art is a 4-state `62x49` button strip;
  nobody has looked at the pixels).

### 3.5 Stale copies — the old "5 proven" was an undercount

Old doc: 5. `coverage_rederive.py`: 27. **My depth-aware count: 32 root ids
built by more than one distinct script instance.** The roots inventory's grading
of *which copy wins* is good discipline and is carried forward intact:

- **PROVEN by rect discriminator:** `0xC991EDA8` → `I-69e3d347`;
  `0xAA3AC002` → `I-cbc3c2b9`; Graphs `0x8A8B5B72`/`0x0A4A8176` → `I-6bc9065a`.
- **UNPROVEN — STRUCTURAL NULL:** `0xE9889775`, `0x6A64E3C0`, `0xAA32BCE6`
  (Data Views 3-way), `0x6A15C767`. Both copies have identical root rects and no
  retained log ever dumped their subtrees, so the discriminator **had nothing to
  see**. The old doc states these as facts. **They are not facts.**
- **NOT stale:** `0xCA35CBED` — both scripts live. Do not prune.

### 3.6 Dev-editor root count

Old doc 25; roots said 4 (it counted only the *uncovered* ones). My
caption-verified count is **24**, each justified by a string read out of its own
script (Lot Configuration Editor, Select Prop/Flora/Building Families, Exemplar/
Cohort editor, Script Console/View/Call Stack/Variables/Breakpoints, Simulator
Control, dev Label Tool twin, Select Foundation, Text Entry). The list lives in
`scratchpad\final.py` and should be moved into a checked-in file when someone
next touches this.

---

## 4. GENUINELY UNMAPPED — 10 root slots, 9 distinct ids

> **Still 10 / 9 as of 2026-08-03 13:00.** Row 1 (`0x6BB92BCB`) had a cure built
> and deployed at 12:39:39 and it would have struck the row — but the cure is
> **measured absent** from the generator and from all three staged tiers at
> 12:44-12:53, **re-confirmed absent at 13:00 by an independent run**. **§0.10
> carries the measurement, the arithmetic for the flip, and the role correction.
> Read it before quoting this section.**
>
> **The count and the headline are UNCHANGED, and that is stated rather than
> left to be inferred:** this row was already counted as UNCOVERED before #98
> was attempted, and it is still UNCOVERED, so **10 root slots / 9 distinct ids,
> D1 288/298 = 96.6%, D1+D2 299/315 = 94.9%** all stand exactly as written. The
> ROLE correction in §0.10a changes what this row *is* — a construction-only
> container whose `area=` is dead data, not a live root — but a role correction
> moves no arithmetic. **Nothing here was improved by this pass.**

These are the entire remaining 3.4%. All are real `cIGZWin` script roots with a
parseable `area=` — **none is structurally unreachable**, so every one is
mappable with the tools we already have.

| # | root | script | 1x | predicted failure | how to map it |
|---|---|---|---|---|---|
| **1** | `0x6BB92BCB` | `I-abb0120f` | 181x296 — **PHANTOM, §0.10** | **2x art in a 1x box** — the 1x box is the two PROMOTED main-window children, **not** this container | cure BUILT+DEPLOYED 12:39:39, **MEASURED ABSENT 12:44-12:53**. §0.10 |
| **2** | `0x6BFAC122`, `0x8BFAC13E` | `I-0bfac164` | 46x108 | Mode C (1x art, doubled frame) | stage art + list id |
| | `0xCBFACAE1`, `0x8BFAC13E` | `I-abfac197` | 46x108 | Mode C | " |
| | `0x27DF05BE`, `0x27DF05BF` | `I-6a9455c9` | 46x97 | Mode C | " |
| **3** | `0x0A41C7B2`, `0x0A41C7B3` | `I-0a41be3e/3f` | 62x49 | Mode C | ~~one `kNeverScaleIds` line~~ **✅ SHIPPED v2.65.0 (#54) — `UiSpike.cpp:4867-4868`** |
| **4** | `0xEACA96DD` | `I-6aca9687` | 94x185 | cosmetic | ⚠ **RECLASSIFIED — do not ship** |

**⚠ 2026-08-16: this section's count is stale — row 3 is CLOSED, and row 2's
third line is half-closed.** Both of row 3's ids are in `kNeverScaleIds`
(`UiSpike.cpp:4867-4868`; array declared at `UiSpike.cpp:4778`), so the "one
`kNeverScaleIds` line" this row asks for has already shipped. That counts as
coverage by this project's own instrument, not just by opinion:
`coverage_rederive.py:234-235` records "v2.65.0 (#54): 79 -> 83. Three Mode C
roots (0x0A41C7B2/B3, 0x27DF05BF) entered kNeverScaleIds" and raises
`distinct_root_ids_named` to 83 (`:244`). **Open item 4 in "Open, in priority
order" ("Tutorial overlays — cheapest build") is the SAME item as row 3** — the
"IDENTITY" section re-identifies `0x0A41C7B2/B3` as tutorial overlays on the
Disaster Tools button and the bullet below calls row 3 "the tutorial overlays" —
so it is discharged, but **by never-scale, not by the dialog-static build
proposed in that bullet.** Row 2's third line (`0x27DF05BE`, `0x27DF05BF`) is
also partly stale: `0x27DF05BF` entered `kNeverScaleIds` in the same change
(`UiSpike.cpp:4873`), while `0x27DF05BE` is deliberately left out because of the
id collision this file already flags in the TRAP note below
(`UiSpike.cpp:4875-4879`). **Also note the in-source warning at
`UiSpike.cpp:4861-4866`: never-scale was chosen over row 2's "stage art + list
id" recipe precisely because that recipe is the shape that shipped #98's 4x
legend and that #100 predicts as 8x at the 2x tier.** Re-derive "10 root slots /
9 distinct ids" — and the "count and headline are UNCHANGED" block at the top of
§4 — before quoting either.

**⚠ AMENDED 2026-08-03 — three of these five rows changed shape. Build order,
gates and risk for each are in `tools\research\FINAL-3-PERCENT.md §4`.**

- **Row 2, the chips, are Mode A — NOT Mode C.** `sub_438390` @ `0x43844C`
  passes `cSC4BaseViewInputControl::windowManager` → `GetMainWindow` (vt+0x0C)
  as the **parent** to the loader. Their frames are never doubled, so **shipping
  selective-safe 2x art for them would manufacture exactly defect #98.** The
  cure is dialog-static static-doubling **plus** a new builder class
  (`RUNTIME_BOUND_1X`, "REAL-BUT-OVERWRITTEN") to keep the runtime-supplied
  36x41 portrait's `imagerect` at 1x.
- **`0x6BFAC122` / `0x8BFAC13E` / `0xCBFACAE1` may not exist in the shipping
  game.** Whole-image immediate scan: **0 hits** for those root ids and 0 for
  their script TGIs, while `I-6a9455c9`'s ids are found 3–5 times each (positive
  control passing). MEASURED null. **Build a SIGHTING, not a cure.**
- **Row 4 `0xEACA96DD` is a CODE-CREATED window, not a scriptable root.**
  `sub_79C800` @ `0x79C822` binds its art `{856DDBAC,46A006B0,144161C0}`
  directly; the game never loads `I-6aca9687`. Editing the script changes
  nothing, and doubling the code-bound art would enlarge it in a window whose
  geometry constants are unread. **Blocked pending a builder census of
  `sub_79C7E0`/`sub_79C800`.**
- **Row 3 the tutorial overlays are the cheapest build** — dialog-static beside
  their own page, art single-referenced, zero collateral.

~~**#1 `0x6BB92BCB` (Trip Types legend) is the one genuine live defect, and it is
one we introduced.**~~

**⛔ CORRECTED 2026-08-16 — #98 IS NOT A BUG. THIS SECTION'S PREMISE IS REFUTED,
AND ITS INSTRUCTION IS A MINE.** The #98 thread in this file (§0.10, §4 row 1 and
its header note, and "Open, in priority order" item 1) is superseded in full. The
load-bearing claim — "No sweep root reaches a main-window child ... So the panel
IS quarter-art today" (:633-636) — is a STATIC INFERENCE and it is FALSE. **The
data-side double WAS shipped once, RENDERED AT 4x ON SCREEN, and was reverted for
that reason**; the three runs at 12:44 / 13:00 / 13:14 that "measured the cure
absent" were measuring that REVERT, not a lost edit. `build_selective_safe.py`
grepping clean for `6bb92bcb` / `abb0120f` is therefore the **CORRECT** state,
not the anomaly this file spends three sections investigating (re-verified
2026-08-16: 0 hits, positive control passing — the same file yields 178
`0x########` matches). ⛔ **Do not re-apply the cure. Do not restore the
adjudicator. Do not ask for eyes-on a cure that must not ship.** Evidence:
`VERSION-HISTORY.txt:3322-3342` (supersession banner) and
`VERSION-HISTORY.txt:2647-2652` (#98 CLOSED NOT-A-BUG, same session; the file is
newest-first, so 2647 postdates 3320). Corroborating in source today:
`0x0BB0F5E7` and `0x6BB92BCA` are both in `kRegionPanelIds`
(`src\UiSpike.cpp:4744-4747`) and `0x6BB92BCA` is also in `kOwnsBackgroundSheet`
(`src\UiSpike.cpp:14425-14430`) — but note the proof that the runtime reaches the
CITY instance is the ON-SCREEN 4x render plus the user-confirmed closure, not a
static read. That is the whole lesson: STATIC DEFECT = HYPOTHESIS, walked into
twice on this same window.

The historical detail is kept below as written. Confirmed at the time via
`tools\sdk\lookup.py`:

- Its 12 art refs are `EXCLUSIVE … 2x-in-place` in `refmap.csv` — **2x art ships**.
- `selective-safe\stage\…I-0xabb0120f.ui` still carries the **1x** root
  `area=(139,81,320,377)` — and so do `stage-15x` and `stage-3x`.
- The id is in **no** runtime list (`SCALED_WINDOW_IDS`, `kNeverScaleIds`,
  `kDataScaledSubtreeIds`, dialog-static — all absent; positive control printed).

~~Stock ships 1x art in a 1x box and looks right. We ship 2x art in that same 1x
box.~~ **FALSE — see the 2026-08-16 correction above.** The box is not 1x at
runtime; the 2x art we ship is drawn into a window the runtime has already
scaled, which is why the added double rendered at 4x. Reachability (Route Query
on any road or rail in a founded city) is unchanged and is now the STOCK-CORRECT
path.

> **⚠ AMENDED 2026-08-03 12:53 — THREE OF THE FIVE BULLETS ABOVE ARE NOW WRONG,
> AND THE QUESTION THEY POSE IS ANSWERED.** §0.10 has the evidence.
>
> - **“12 art refs” is 14** — 13 EXCLUSIVE/2x-in-place plus one SHARED
>   (`0x14416245` -> clone `0x47026244`).
> - **The 1x `area=(139,81,320,377)` is DEAD DATA, not the defect’s box.**
>   `0x6BB92BCB` is destroyed by its own creator `0x218` bytes after it is made
>   (`ChildDelete` at `0x004C5B64`) and never enters the window tree.
> - **“The id is in no runtime list” is true and is no longer the point.** The
>   windows that draw are `0x0BB0F5E7` and `0x6BB92BCA`, promoted to children of
>   the MAIN WINDOW — and ⛔ **both are already in `kRegionPanelIds`**, so a
>   city-side runtime entry would be **4x**. The cure is data-only for that
>   reason.
>
> **The question posed in the next paragraph — “does the city sweep reach it?” —
> is ANSWERED, and offline: NO.** No sweep root reaches a main-window child
> (city = `SC4View3DWin`, region = `0xEA659793`, neither id in `kCityDialogIds`).
> So the panel IS quarter-art today, and one observation is no longer needed to
> decide it. What an observation is still needed for is **eyes-on acceptance of
> the cure** — which has not happened, and which cannot happen while the cure is
> absent from the build (§0.10b).

**The measurement session needs exactly one answer per root: does the city sweep
reach it?** For `0x6BB92BCB` that flips the outcome entirely — if the sweep
doubles the window, the 2x art we already ship becomes correct and nothing else
is needed; if it does not, the panel is quarter-art today. One `[Probe]` run
covering Route Query + a tutorial + a city with Sims covers all four items.

**⚠ TRAP — `0x27DF05BE` is an ID COLLISION.** It is built by `I-6a9455c9`
(46x97 occupant chip) **and** `I-2a41436c` (339x200 "Obliterate City" confirm,
already static-doubled). Any id-keyed rule hits **both**. The chip needs 1x art
in a doubled frame; the dialog is already correct. Read this before touching #2.
It is also why `0x27DF05BE` shows as "seen live" — that sighting is almost
certainly the *dialog*, not the chip.

---

## 5. ~~STRUCTURALLY UNREACHABLE — proven, not assumed~~ — ⚠ TWO OF THREE ROWS REFUTED, see §0.3

> **This section as originally written is WRONG and is kept only so the failure
> is legible. The corrected table is §0.3. Do not cite the strikethrough rows.**

The law it invoked: *the SC4 UI buffer class never composites to screen, so
full-screen elements are renderer-drawn and unreachable by the cIGZWin tree.*
The law is fine. The proof standard was not: **`children=0` is a state
observation, not a structural fact**, and this section treated it as one.

| window | what was claimed | 2026-08-03 verdict |
|---|---|---|
| ~~`0x2BA6BB97` `cSC4WinRegionView`~~ | ~~PROVEN — region map content is code-painted~~ | **REFUTED.** 13 descendants printed at `snapshot.log:151-165` the moment a city tile is clicked. **COVERED** by dialog-static; #72 user-confirmed. §0.3 |
| ~~`0x6A5E44B6` — identity UNKNOWN~~ | ~~PROVEN unreachable-by-data~~ | **REFUTED on both halves.** It is `cSC4WinAlertBorder` (clsid `0xCA5D3294`, vt `0x00AB5B48`, `Plot 0x00794100`), fixed as #59 in v2.37.2 **three days before this row was written**. **COVERED** by art + the ≥90% sweep skip at `UiSpike.cpp:7630`. §0.2 |
| City LOADING / SAVING screen | no `.UI` exists at all; never appears in the tree | **STANDS** — 100% code-painted |

**The four "not yet adjudicated" items are now adjudicated** (full proof in
`tools\research\FINAL-3-PERCENT.md §3`):

| item | verdict |
|---|---|
| `0x6A0AF41D` | UNCOVERED, **cosmetic — leave alone**. A particle emitter (`Plot = sub_7A9D60`) drawing four 128x128 DXT3 cloud sheets; sprite size is `float @0xAB7E10 = 128.0`. Resizing the window is a no-op (bounds latched once at init). |
| `0x4C30E4FA` | COVERED but AT-RISK; it is a **My Sims world-anchored callout** (`ShowWindow` at `0x00431130`), ×6 pooled, and the `kCityDialogIds` label is unsupported. |
| `0x00000043` | **UNCOVERED, defect quantified: 10 px clip at birth, 20 px after our own sweep** — and it exists only because *we* ship 2x art for TGI `{856DDBAC,46A006B0,53244588}`. |
| `0x42B7C351/53/54/55` | COVERED (mechanism present, pixel-unverified). It is the **generic GZ scrollbar family** — every scrollable control in the game carries these four ids. Hazard: `ScaleMenuFlyouts` walks the same subtree with `centerLeaves=true`, which would freeze the 24x25 buttons at 1x if it won the order race. |

### The denominator's blind spot — CLOSED (partly)

The census of code-created windows exists as of 2026-08-03
(`tools\uimap\wincensus.py` → `_work\wincensus.json`). It found **17 named
shipping code-created windows**, which is why the headline moved to 94.9%
(§0.1). It is **not exhaustive**, and §0.1 names the three channels that bound
it from below but not from above. **Any statement of the form "N% of the UI is
covered" is still a statement about the windows we can NAME.**

---

## 6. COVERED BUT UNVERIFIED — 28 ids, and why the null is weak

Mapped, mechanism attached, **never observed in any retained log**:

```
0x000A0000  0x0A551C53  0x0A5BA192  0x0A8CD3EE  0x0C525B9E  0x10000006
0x2A57CB82  0x2A57DB82  0x4A35B0F2  0x4A5BA0E7  0x4A9DB60C  0x4BCB938A
0x6A243D9E  0x6A5BA20C  0x6AAEEC4A  0x8A5AB1D0  0x8A8DFCF5  0x8BB27C12
0xAAA9C9D9  0xAB954023  0xCA5E6261  0xCBF32603  0xEA53F5DB  0xEA5BA0D1
0xEA5E748C  0xEBB16D71  0xEBBC081E  0xEC1A5CBF
```

### NULL DISCIPLINE — read this before treating that list as a risk ranking

**POSITIVE CONTROL FAILS.** `0x4BCB938A` — the U-Drive-It console, *known live*,
the subject of closed task #93 — **is in that list.** It has never appeared in a
retained log either. The instrument that would have caught it was armed; the
*session* was not kept.

Therefore every entry above is a **WEAK MEASURED NULL** attributable to log
retention, **not** evidence of unreachability. Two supporting measurements:

- **Retention is lossy.** `Logger` recreates the `.log` each launch and
  `Deploy-OnGameClose.ps1` archives none. 14 logs survive; the busiest versions
  left nothing.
- **The full-tree instrument is dark.** `UI id=` lines by log: 553 / 330 / 274 /
  216 / 60 / 42 in the six oldest, and **0 in all five modern logs** (through
  v2.54.4). `DumpTree` is gated on `settings.spikeDumpTree`, shipped `0`.

~~Note also that live-evidence's finding that DPROBE is **armed at compiled
defaults** (the `[Probe]` ini read sits behind `static int s_poll … >= 20`, so
the ini band never takes effect) means our only *discovery* instrument is
scoped to ~14.7% of the screen and caps silently at 30 lines. Both are cheap
fixes and both gate the measurement session's value.~~

**CORRECTED 2026-08-16 — both halves of this are now false, and in OPPOSITE
directions. Verified against current source.**

1. **The `[Probe]` ini read is no longer poll-gated.** The guard is
   `const bool firstPass = !s_readOnce;` (`src\UiSpike.cpp:11971`) /
   `if (firstPass || (s_liveTune > 0 && ++s_poll >= 20))` (`:11972`), so the block
   runs on the FIRST pass through `ScaleGodFlyouts` and reads
   `[Probe] Enabled / BandL / BandR / BandT / BandB / Max` right there
   (`:12030-12041`). A user's band DOES take effect. The code says so itself:
   "its ini says [Probe] Enabled and that is read at startup (and re-read under
   LiveTune=1)" (`:318-320`). Reachability is not in doubt — `ScaleGodFlyouts`
   (`:11914`) has one early return (`if (!pView)`) and runs on the tick
   (`:6694`, "built to run 60x/sec" at `:6647`). The residual limitation is the
   REVERSE of what this paragraph claimed: there is no ONGOING re-read unless
   `[UiSpike] LiveTune=1`, so a mid-session `[Probe]` edit needs a game restart
   (`s_readOnce` is a function static and nothing resets it).

2. **DPROBE is NOT "armed at compiled defaults" — at compiled defaults it is
   OFF.** v2.69.3 flipped the compiled default from 1 to 0: `int gProbeOn = 0;`
   (`:322`), because a shipped install whose clean ini has no `[Probe]` section
   was running the band walk every 16 ms for output the user can never consume
   (`:314-320`). The emit site is `if (gProbeOn && changed && inBand && logged <
   gProbeMax)` (`:12606`), so a shipped install logs nothing at all. The band
   (`gProbeL=-150 / gProbeR=500 / gProbeT=380 / gProbeB=1250`, `:501-504`) and the
   30-line cap (`gProbeMax = 30`, `:505`) do still bound the output — but only
   once a dev ini opts in with `[Probe] Enabled=1`. (The "~14.7% of the screen"
   figure is carried over from the original note; it was NOT re-derived here.)

So the "cheap fix" of un-gating the ini read has already shipped, and the
recommendation below that still asks for it is stale for the same reason.

**Cheapest high-yield action, unchanged from live-evidence's recommendation:**
set `DumpTree=1`, un-gate the `[Probe]` ini read, widen the band to the full
frame with `Max=2000`, play one session covering Budget → Advisors → My Sims →
U-Drive-It → all 18 Graphs → Data Views → Route Query → a tutorial, **and
archive the log**. That single session converts most of this section from
unknown to measured.

---

## 7. ~~crosscheck.py — GREEN~~ — ⛔ **RED as of 2026-08-16: 16 MISSES**

> **⛔ RE-MEASURED 2026-08-16 — BOTH TRANSCRIPTS BELOW ARE DEAD, AND SO IS THE
> "9 SKIPPED" TABLE AT THE END OF §7.** Re-run from the project root, exit code
> read directly rather than through a pipe:
>
> ```
> SUMMARY: 293 CodePatches entries = 278 adjudicated (262 passed, 16 MISSED)
>          + 0 deferred + 15 skipped                                 exit 1
> CodePatches.cpp tables parsed: 43 (278 adjudicated entries, 0 deferred, 15 out-of-scope)
> EXTRAS (the model found it, CodePatches does NOT patch it): 41
> FAIL: 16 patched site(s) are outside the offline model.
> ```
>
> **The 8 DEFERRED are gone, and legitimately.** `crosscheck.py:428` now reads
> `DEFERRED = {}`; the header at `:401-427` records the close — `0x76D3D0`
> promoted into `census.EXTRA_BUILDERS`, the five `kGraphLegendImmSites` covered
> by geomextra RECORDER D, the three `kGraphLegendBlocks` by RECORDER E. Both
> #57 tables now print in the parsed-table list with **no** `[out of scope]` tag
> and appear in **neither** MISSES nor SKIPPED: adjudicated, and passing.
>
> **The 16 MISSES**, each printed with its owner: `kRegionBuildFn`,
> `kRegionItemBuildFn`, `kRegionOverlayFn`, `kRegionInvalidateFn`,
> `kRegionPanClampFn`, `kRegionCamScaleSite`, `kRegionCamSetScale` (7);
> `kIntroVidSites` (4); `kCostBoxHeightSite`, `kCostBoxWidthSite`,
> `kCostOriginSite`, `kCostOriginBack` (4); `kAdviceRowWinSite` (1). The tool's
> own G1 guard prints the model's age — `constants.json 2026-08-04 07:46:37` vs
> `CodePatches.cpp 2026-08-15 17:32:47` — so for the first 15 the reading is a
> **stale model**: they were patched after the model was last built.
>
> **`kAdviceRowWinSite` is a different animal, and regenerating the model may
> not clear it.** It is #136's 19-byte EQUAL-LENGTH RE-ENCODE window that
> *contains* `kAdviceRowMidSite` (`src\CodePatches.cpp:412-419`), rewriting
> `sub esi, imm8` as `lea esi, [eax - imm32]`, with its own byte gate
> (`tools\uimap\emu\gate_advice_rowx.py`, 4 positive controls).
> `kAdviceRowMidSite` **adjudicates and passes in the same run.** Block
> re-encodes of exactly this shape — `kOrdinanceNameXBlocks`, `kGlRow0Site` —
> are PERMANENT **skips** by the gate's own printed reason text, not misses. So
> this entry is a **categorisation gap, not a census gap**; decide which bucket
> it belongs in rather than waiting for a regeneration to absorb it.
>
> **`kRatingImulSites` is no longer skipped.** The 3 mayor-rating `imul` sites
> now adjudicate and pass (no `[out of scope]` tag, absent from both SKIPPED and
> MISSES). The row for them in §7's closing table below — "deliberately not
> attempted … shipping a wrong unit is worse than a printed skip" — is **DEAD**.
> Today's 15 skips span **10** tables, every one marked PERMANENT:
> `kPopupStyleRetargets` (4), `kX8DispatchSite`/`kX8StubBlock`/`kX8TableVa`/
> `kX8TailVa` (4), `kOrdinanceNameXBlocks` (2), `kTipWrapSites` (2),
> `kGlRow0Site` (1), `kRatingUpdateVa` (1), `kDeclineStepVa` (1).
>
> **Until `constants.json` is regenerated, do not reason about the
> region-screen, intro-video or cost-box families from the offline model.**

> ### ⚠ AMENDED 2026-08-03 12:03 — THE GATE GAINED A CATEGORY AFTER THIS WAS WRITTEN
>
> This section was measured at 12:00 and was true then. `crosscheck.py` was
> edited at **12:03** and the transcript below **no longer reproduces**. What
> it prints now:
>
> ```
> SUMMARY: 268 CodePatches entries = 251 adjudicated (251 passed, 0 MISSED)
>          + 8 deferred + 9 skipped                                exit 0
> 21 CodePatches.cpp tables parsed (251 adjudicated, 8 deferred, 9 out-of-scope)
> ```
>
> The eight are the **#57 graph-legend sites** (`kGraphLegendBlocks` +
> `kGraphLegendImmSites`, owner `sub_76D3D0`), added to `CodePatches.cpp` by
> v2.55.0 **after** this file's own recipe was run. They are held in a new,
> explicitly-named **`DEFERRED`** bucket (`crosscheck.py:63-89`, `:298-337`),
> counted apart from passes *and* from skips, guarded by G1–G4 (including a
> **printed positive control**: `sub_76D3D0` is in `builders.json →
> discovered`, so the null is MEASURED, not structural) and expired
> automatically at `:430` once the model learns the sites.
>
> ⛔ **And the claim in the very next paragraph — "the gate did not go green by
> narrowing" — must now be read with a date on it.** It was true of the 12:00
> green. **The 12:03 green DID come from adding a category**, and the honest
> statement is: the gate is green over a scope that is **17 entries narrower
> than `CodePatches.cpp`** (8 deferred + 9 skipped). The tool says so in its
> own summary. Quote the whole line, never the colour.

```
python tools\uimap\crosscheck.py   →  exit 0
SUMMARY: 251 checked, 251 passed, 9 skipped
MISSES (CodePatches patches it, the model does not know it): 0
EXTRAS (model found it, CodePatches does not patch it): 33
19 CodePatches.cpp tables parsed (251 in-scope, 9 out-of-scope)
```

Exit code measured directly, not through a pipe. **[TRUE OF THE 12:00 RUN — see
the amendment above.] The gate did not go green by
narrowing:** scope is identical before and after (19 tables / 251 in-scope /
9 out-of-scope); the model *grew* (constants sites 292→307, EXTRAS 30→33,
builder owners 12→16). All 12 former MISSES were category **(a) real gap** —
places the census structurally could not reach the owner:

| was | owner | why it was invisible |
|---|---|---|
| 8 | `sub_7A04F0` Data Views legend | `SetArea(const Rect*)` passes a **pointer**; constants are four dword stores into a stack rect |
| 3 | `sub_7EAEB0` sub-flyout provider | `SetItemMetrics` is vt+0x30 on class `0xAB6D28` — **not a cIGZWin slot** |
| 1 | `sub_793810` advice row | 0 direct callers (vtable-entered); geometry is `GetW − 61` |

### ~~The 9 SKIPPED checks — every one, with its reason~~
### The SKIPPED checks — ⚠ AMENDED 2026-08-16: **10 tables / 15 entries**, not 3 / 9

**See the RED block at the top of §7.** The `kRatingImulSites` row below is DEAD
(those 3 sites now adjudicate and pass); the two surviving rows,
`kPopupStyleRetargets` (4) and `kTipWrapSites` (2), are still skips, but this
table no longer enumerates *every* skip — 8 more tables were added after it was
written.

A SKIPPED entry is **not** a pass. It is a question this gate does not ask.

| table | n | reason | to resolve |
|---|---|---|---|
| `kPopupStyleRetargets` | 4 | **Font-style GUID retargets** in `sub_52CC50` / `sub_762F20`. Not geometry at all — they swap a style id, and `constants.json` holds only `x/y/w/h/l/t/r/b/gap`. | Nothing here. Belongs to a style map the offline model does not have. Correctly out of scope. |
| ~~`kRatingImulSites`~~ | ~~3~~ | ~~**Mayor rating bar, not a window rect.** An `imul` scales a percentage into a bar length inside `sub_7E8510`.~~ | ~~Promote `0x7E8510` into `census.EXTRA_BUILDERS` and teach `constants.py` an imul-on-a-measure role. Deliberately not attempted: the value is a **ratio**, so the model needs a *unit* as well as a number, and shipping a wrong unit is worse than a printed skip.~~ **✅ RESOLVED 2026-08-04 (Phase 1 close-out) — the promotion this cell called "deliberately not attempted" WAS done.** `0x7E8510` is in `census.EXTRA_BUILDERS` (`census.py:245-258`); `kRatingImulSites` left `PERMANENT_OUT_OF_SCOPE` (`crosscheck.py:290-298`). The unit worry was answered by **OPACITY**, not by guessing a unit: the imuls record with their true encoding and value under roles that claim no rect semantics — `'w'` from the documented SetW arg spec (slot +0xCC, foreign-slot allowlisted for this owner only), `'pushed'` for the GZWinMoveTo coordinate. See `BUILDER-CENSUS.md:638-646`. Re-verified 2026-08-16: the run prints `kRatingImulSites  3 entries` with **no** `[out of scope]` tag, and none of its VAs is in the MISSES list — all 3 adjudicate and pass. |
| `kTipWrapSites` | 2 | **Tooltip wrap width** inside `sub_798710`, feeding the HTML text engine rather than a `cIGZWin` rect. | One measurement — confirm from a live log whether the wrap width reaches a window `SetSize` at all. Per `SC4-UI-ENGINE.md` the rich-text sizes live in `.rdata` tables the window tree never touches, so this may be **structurally outside any cIGZWin model**. |

**⚠ AMENDED 2026-08-16 — this table lists 3 tables / 9 entries; the tool skips 10 tables / 15 entries today.**
Measured from `python tools\uimap\crosscheck.py` on 2026-08-16, whose own SUMMARY line reads
`278 adjudicated (262 passed, 16 MISSED) + 0 deferred + 15 skipped`:

- `kPopupStyleRetargets` 4 — font-style GUID swaps (in this table already)
- `kTipWrapSites` 2 — HTML text-measure, +0x1C on a non-window object (in this table already)
- `kOrdinanceNameXBlocks` 2 and `kGlRow0Site` 1 — **equal-length block re-encodes**,
  adjudicated by their own byte gates `tools\uimap\emu\gate_ordinance_namex.py` and
  `gate_graphlegend_leftanchor.py`, not by this constant model
- `kRatingUpdateVa` 1 and `kDeclineStepVa` 1 — **MinHook target VAs** (#130 decline-arrow
  anchor hook); a hook VA holds no rect
- `kX8DispatchSite`, `kX8StubBlock`, `kX8TableVa`, `kX8TailVa` — 1 each = **4**, the #121
  minimap x8 bake family: a jump-table dispatch, adjudicated by
  `_tests\Test-MiniMapX8Bake.py`, **not** by any gate under `tools\uimap\emu\`

4 + 2 + 2 + 1 + 1 + 1 + 4 = **15**. Six of the ten tables above have no row in this table
at all. **Read the tool's own SKIPPED block, not this table** — `crosscheck.py:303-389` is
the source of truth, and every entry there is now classified PERMANENT with a stated
falsifier rather than an open "to resolve".

**Residual scope caveat, stated out loud:** the census now holds **16 of 552**
rect-driving functions. The gate is green *over its stated scope*, which remains
much narrower than "all of the UI". The tool prints this in its own closing
lines rather than letting a reader infer otherwise.

---

## 8. Carried forward from the old doc (still current)

**Inside covered roots — un-leverable by art.** Runtime-pixel nodes (`imagerect`,
no `image=`): My Sims portraits `0x22220000-04` + `0x22220055`, `0x8A1F1EEF`
(100x100), `0xABBAA2D3` `ir=5,5,695,130`, budget `0xAA3AC000/1` `ir=0,0,100,100`
×2 each. ~~Code-painted classes un-levered: `0xAA5C2F86` TrendBar (buffer
unverified), `0x28C5A41F` (in Data Views, UNIDENTIFIED), `0xC7A0E17E` (in status
panel, UNIDENTIFIED) — the last two sit in always-visible HUD roots and are the
highest-value probes.~~ **Refmap art gap inside covered roots: ZERO untouched
refs remain** — re-verified today, byte-identical to the v2.27.3 cached report.

**⚠ AMENDED 2026-08-03 — all three "UNIDENTIFIED code-painted classes" are
resolved, and none is a probe target.** They are `clsid=` values, not window ids:

- **`0x28C5A41F` is not a window id at all.** It is the clsid of the Data Views
  **Map-View page**, declared in `I-0b72f276`, `I-2bc9060f` and `I-ea287193` as
  `clsid=0x28c5a41f iid=IGZWinCustom id=0x00004200` — the page that hosts
  scrollbar `0x42B7C351` and that the code addresses directly as a **depth-1**
  loader handle (§0.6).
- **`0xAA5C2F86`** (TrendBar, 145x9) and **`0xC7A0E17E`** (status-panel meters,
  71x4 and 8x71) appear in the corpus **only as `clsid=`, on nodes carrying no
  `id=` at all.** They are anonymous, and they are scaled today purely because
  their parent root is swept — which is the general proof that **the sweep is
  structural, not id-keyed** (§0.5).

**Uninsured-but-fine dialogs.** `0x0A592004`, `0x0A5BA192`, `0x0A8CD3EE`,
`0x2A96ED21`, `0x6A4D0A59`, `0x8A5AB1D0`, `0xEBBC081E` are static-doubled but
named nowhere in `UiSpike.cpp`. Safe by architecture — `UiSpike.cpp:12464-12472`
parents transient region dialogs to the main window and `DockDialogs` defaults
**false** (`Settings.h:252`), so the sweep never reaches them and they cannot go
4x. But the project's own policy (`UiSpike.cpp:3169-3173`) says they should be
in `kNeverScaleIds` anyway. **Absent insurance, not a live bug.** One-line,
zero-risk hardening.

**Bucket E caveats.** Soft-E: `I-e9263d4c` "Text Entry" and `I-e9263d4e` "Select
Foundation" carry `captionres` (the localization tell-tale fails); reachable only
via Lot Editor. `I-cb40cfdc` is the DEV twin of the shipping Label Tool —
different root ids.

**Live trap.** `DockDialogs=1` would 4x the six region dialogs (runtime dock
table and dialog-static now overlap on the same six). Keep it `0`, or remove one
mechanism first.

---

## 9. What changed on 2026-08-03, and why

| change | why |
|---|---|
| Denominator 304 → **298**; 8 third-party plugin roots excluded | They are other people's mod UI. **This narrowing flatters the ratio ~0.2pp and is disclosed, not buried.** |
| Coverage 94.7% → **96.6%** | Numerator unchanged at 288; 6 of 16 uncovered roots genuinely fixed since 07-29. |
| Added the **60.9% live-observation** figure | Mechanism-coverage alone was being read as "it works". It does not mean that. |
| Added §5 **structural-unreachability proofs** + the code-created blind spot | The old doc had no such bucket; "N% of the UI" was overclaiming. |
| Bucket D 16 → **10 root slots / 9 ids** | Items 1, 3, 4, 5, 9 verified closed in current source. |
| `0x0A41C7B2/B3` re-identified as **tutorial overlays on the Disaster Tools button** | Disassembly reproduced from the exe; reconciles the script's own `tiptext` with the code. Old "Establish/Obliterate" entry was wrong. |
| Bucket F "5 stale copies" → **32 multi-script root ids**, graded PROVEN / UNPROVEN | Four of the old doc's stale-copy verdicts are **structural nulls stated as facts**. |
| Flagged the `coverage_rederive.py` **first-`<LEGACY>`-only defect** | Its 85.8% has the wrong denominator and was being quoted as an independent check. |
| crosscheck recorded **GREEN**, with all 9 SKIPPED entries enumerated | A red gate that stays red teaches the team to ignore it (#96). |

## 9b. What changed later on 2026-08-03 (the amendment)

| change | why |
|---|---|
| Headline **96.6% → 94.9%** (299/315) | The code-created census landed. The denominator grew by 17 named windows; the numerator by 11. **Coverage fell — reported plainly.** §0.1 |
| §5 rows for `0x2BA6BB97` and `0x6A5E44B6` **struck** | Both refuted by measurement. `children=0` was a state observation, and #59/#72 had already shipped fixes into both. §0.3 |
| `0x6A5E44B6` **named** `cSC4WinAlertBorder` | It had been named 3 days earlier (#59, v2.37.2). This file was stale, not the game. §0.2 |
| Ordinances `0x0423278D/E/F` **UNCOVERED → COVERED** | We ship byte patches *and* a sweep pin for them. The census's "no mechanism" was wrong; its causal finding (code-created, no `.UI`) was right. §0.2 |
| `0x00000043` promoted to a **quantified defect** | 10 px at birth, 20 px after our own sweep, caused by art *we* ship. §0.2 |
| The four "not yet adjudicated" items **adjudicated** | §5 replacement table. |
| Added §0.4: **36 unexplained live ids collapse to ONE family** | A 21%-of-live "hole" is one already-covered family. The biggest de-escalation in the batch. |
| Added §0.5: **the sweep is structural, not id-keyed** | Explains why a large anonymous residual is low-risk, and closes §8's three "UNIDENTIFIED" entries. |
| Added §0.6: **depth-1 loader handles** are a second denominator gap | `0x00004200` is passed as a winId; the ladder counts depth-0 only. |
| Added §0.8: **42% of corpus ids are multi-declared** | Collisions are the mode. Every id-keyed rule we ship is already a multi-window rule. |
| Added §0.9: **all pre-amendment line numbers are stale** | v2.55.0 moved `UiSpike.cpp` by 20–40 lines the same day. |

## 9c. What changed again later on 2026-08-03 (the doc-consistency audit)

No new census work. A cross-document audit found this file and the
then-current HANDOFF.md session diary (retired 2026-08-06 and superseded by
`START-HERE.md`; the diary itself was archived to the gitignored `_archive\`
and is not part of this repo)
disagreeing on four claims, and both of us disagreeing with the tools on disk.
Resolution rule applied throughout: **the measured value wins, the loser is
corrected in place with a dated note, nothing is deleted.**

| change | where | why |
|---|---|---|
| §7's crosscheck transcript marked **AMENDED** | §7 + *How to reproduce* | The gate was edited at 12:03, three minutes after this file was saved. It now prints **8 DEFERRED** alongside the 9 skips. Both the transcript and the "did not go green by narrowing" claim were true at 12:00 and are not true of the current tool |
| HANDOFF.md corrected to **94.9%**, and its Q2 / `0x2BA6BB97` / `0x6A5E44B6` claims struck | HANDOFF.md §5 (retired 2026-08-06, archived out of the repo — see the note above §9c's table) | It was saved at 11:55, five minutes before this file's amendment, and carried 96.6%, "no census of code-created windows", "proven structurally unreachable" and "identity unknown" — all four superseded here at 12:00 |
| The v2.53.0–v2.55.0 release finally **written to `VERSION-HISTORY.txt`** | root changelog | There was no entry for v2.53.x, v2.54.x or v2.55.0 at all; the newest #57 entry still ended on the *refuted* cached-buffer theory |
| `sub_76D3D0`'s absence recorded **inside the generated model docs** | `BUILDER-CENSUS.md`, `CONSTANT-MAP.md` | The builder and its six budget constants existed only in prose. That is the structural reason `crosscheck.py` needed a DEFERRAL rather than a pass — worth saying in the files that would otherwise look complete |
| **STATE OF THE MODEL** written | `emu\README.md` | An honest four-bucket account of what the emulator can adjudicate, what is measured, what is assumed, and what it still cannot see (starting with: it never looks at a pixel) |
| Task **#54** title still says 96.6% | task list | Flagged, not silently edited — it is the same supersession as §0.1. *(Re-checked 2026-08-03 afternoon: the title now reads "94.9% = 299/315, D1+D2". Row kept as the record of the flag; the flag itself is discharged.)* |

## 9d. What changed again on 2026-08-03 (#98, the Trip Types legend)

| change | why |
|---|---|
| `0x6BB92BCB` re-described as a **construction-only container**, its `area=` as **dead data** | Measured from the exe: created at `0x004C595C`, `ChildDelete`d by the same function `0x218` bytes later at `0x004C5B64`. §4 called it a live root with a 1x box; the box is a **phantom**. §0.10a |
| The two real windows named: **`0x0BB0F5E7` and `0x6BB92BCA`, promoted to MAIN-WINDOW children** | This is the mechanism, and it is the reason no sweep root reaches them and the reason the cure has **no runtime half**. §0.10a |
| ⛔ **Never add either id to a CITY runtime list** — both are already in `kRegionPanelIds` | A city-side entry on top of the region entry is **4x**. The region legend is a different script (`I-abc0ed33`). §0.10a |
| Art-ref count **12 → 14** | 13 EXCLUSIVE/2x-in-place + 1 SHARED (`0x14416245` -> clone `0x47026244`). §0.10a |
| §4's open question **"does the city sweep reach it?" — ANSWERED OFFLINE: NO** | It was posed as needing a live observation. It did not; it needed the creator disassembled. §4 |
| The headline **stays 94.9%**, with the 97.0% / 95.2% arithmetic shown but **not applied** | A cure was built and deployed at 12:39:39 and is **measured absent** from the generator and all three staged tiers at 12:44-12:53. Nothing on disk supports the higher figure. **Reported as the worse of the two readings, deliberately.** §0.10b |
| Recorded that counting #98 would give "covered" a **third arm** (`tools\selective-safe\` alone, no runtime half) | Same disclosure discipline as the 8 third-party exclusions in §9: a widening that flatters the ratio gets written beside the number. §0.10b |
| The absence **re-confirmed at 13:00** by an independent run that had been briefed the opposite | A second session was told the cure was present and deployed. It measured first. All four probes reproduced, positive control included. This **rules out a transient** but still names **no cause**. The rule it demonstrates: *believe the file on disk, not the build record.* §0.10b |
| Stated explicitly that §4's counts and both headlines are **UNCHANGED** by #98 | The row was already counted UNCOVERED and still is, so 10/9, 96.6% and 94.9% all stand. A ROLE correction moves no arithmetic — said out loud rather than left as a silent non-change. §4 |


### Open, in priority order (revised)

1. ~~**`0x6BB92BCB` Trip Types legend (#98)** — highest reach × severity, a defect
   we introduced.~~ **⛔ CLOSED NOT-A-BUG 2026-08-16, USER-CONFIRMED ON SCREEN.
   Not open, not a defect, and NOT to be re-applied** — sub-item (i)
   "re-establish that the cure is in the generator" is void (its absence is
   correct) and (ii) eyes-on is void (there is nothing to accept).
   `VERSION-HISTORY.txt:3322-3342`, `:2647-2652`.
   ~~One observation decides whether it is a build or a close.~~
   ~~**It was a build, and the build was made.** The sweep question is answered
   offline (NO — the drawing windows are main-window children), the cure is
   data-only, it carries an in-generator adjudicator, and it was deployed
   12:39:39. **Two things are now open, in this order:** (i) **re-establish that
   the cure is in the generator at all** — measured absent 12:44-12:53, §0.10b;
   (ii) **eyes-on acceptance** (Route Query on any road or rail in a founded
   city). DEPLOYED, **NOT user-confirmed**.~~
2. **The batched eyes-on session** — arm `DumpTree`, un-gate `[Probe]`, widen the
   band, **archive the log**. Exact 10-step click path in
   `FINAL-3-PERCENT.md §6`. This is the bottleneck for six open items at once.
3. **`0x00000043` Restore-Toolbars** — the only other quantified defect. Coupled
   pair: tier-generalise `0x1C` at `0x007EE15A` **and** `kNeverScaleIds` with a
   parent check.
4. ~~**Tutorial overlays** — cheapest build, zero collateral.~~
   **✅ CLOSED 2026-08-16 — same item as §4 row 3, shipped v2.65.0 (#54).** Both
   ids are in `kNeverScaleIds` (`UiSpike.cpp:4867-4868`), and
   `coverage_rederive.py:234-235` counts the change. Discharged **by
   never-scale, not by the dialog-static build** proposed in §4.
5. **Occupant chip `I-6a9455c9`** — dialog-static + the new `RUNTIME_BOUND_1X`
   builder class. **They are Mode A; do not ship selective-safe 2x art.**
6. ~~**`kCityDialogIds` `0xAA921F4F` fourth base `330x109`** — one-line data gap,
   latent v2.39.14 shape. §0.7.~~
   **✅ CLOSED 2026-08-16 — shipped v2.64.0 (#102).** `bw[4]/bh[4]` at
   `UiSpike.cpp:14713`, `330x109` in the row at `:14775`, loop bound derived at
   `:15064`. See §0.7.
7. **Re-derive `0x4C30E4FA`'s label** before anything keys off it.
8. **Sighting only** for `0x6BFAC122`/`0x8BFAC13E`/`0xCBFACAE1` — they may not
   exist in the shipping game.
9. **`0xEACA96DD`** — blocked; needs a builder census of `sub_79C7E0`/`sub_79C800`
   first. Do not ship art.
10. **`0x6A0AF41D` clouds** — recommend permanently closing as cosmetic-by-design.
11. **Re-run the root ladder over all depths** (§0.6) and **separate window ids
    from LTEXT keys** in the 21 `sub_779660` literals (§0.1).

---

## How to reproduce

```
python tools\uimap\crosscheck.py                  # exit 0, 251 adjudicated (251 pass, 0 MISSED)
                                                  #        + 8 DEFERRED + 9 SKIPPED
                                                  # (was "251/251, 9 skipped" before 12:03; the
                                                  #  8 deferred are the #57 sub_76D3D0 sites)
python tools\uimap\coverage_rederive.py           # NOTE: §3.2 defect
python tools\sdk\lookup.py 0x6BB92BCB             # step 0 for any id
python tools\research\_checkpoints\pds-cache\art_coverage.py
```

The 330/298/288 census and the live scan were produced by five throwaway
scripts written in the session scratchpad — recount, bucket, caps, final and
livescan. They were one-off instruments, never shipped and never checked in,
so no such files exist in this repo. **The scratchpad is volatile** — anyone
continuing this work
should re-derive from the recipe in §2 rather than expect those files to exist,
and should fix `coverage_rederive.py` (§3.2) so the census has a checked-in home.

Exe fingerprint for every disassembly quoted here: `1189720d5e15b0e1`,
7876608 bytes (`SimCity 4.exe` 1.1.641.0 Steam).
