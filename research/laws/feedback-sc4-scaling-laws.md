# The SC4 UI Scaling Laws

SimCity 4's user interface is a closed-source C++ window system (GZWin) driven by
binary `.UI` scripts, bitmap art bound by TGI, and geometry constants compiled
into the executable. Rescaling that interface — making every widget larger at a
high native resolution rather than upscaling the whole frame — means changing
numbers that four different producers compute independently, in an engine that
was never designed to be resized.

These are the rules that survived contact with it. Each one is stated as a single
present-tense claim followed by the mechanism and the measurement that establish
it. Every law here was earned from a defect that reached the screen; the numbers
are stable and are cross-referenced from the rest of the corpus, so they are never
renumbered.

Read this file before changing `UiSpike.cpp`, `CodePatches.cpp`, the art upscaler,
or any `.UI` generator.

## Vocabulary

- **f** — the scale factor. Shipping tiers are 1.5x, 2x and 3x; 1x is stock.
- **The sweep** — the runtime walk (`UiSpike`) that finds live windows on a tick
  and rewrites their geometry. `ScalePanelRoot` enters a panel, `ScaleSubtree`
  descends it, `Classify` decides whether a window has already been handled.
- **Data pre-scale** — geometry shipped already multiplied in a `.UI` script, so
  the window is born correct and the sweep never touches it.
- **Static builders** — `build_dialog_static.py` and `build_selective_safe.py`,
  which emit the shipped `.UI` datasets.
- **Born-scaling** — making a window arrive at its final size, by data or by a
  create-time detour, instead of correcting it afterwards.
- **Edge-derived vs size-derived** — a window scaled as
  `ScaleRound(l+w,f) - ScaleRound(l,f)` (edges land on the grid, abutting
  siblings stay abutting) versus `ScaleRound(w,f)` (the size is exact, the
  position is untouched).
- **`ScaleRound`** — the single rounding convention, `floor(v*f + 0.5)`.
- **Tier** — one shipping scale factor plus the screen resolution it assumes.

---

### 1. Runtime is sometimes structurally too late — fix it in data

Where the game reads geometry before the first sweep can run, no timing trick
wins. 3D advisor heads are framed when they are bound at city load; the ticker
marquee's width is cached at init and re-imposed on every roll tick. Ship that
geometry pre-scaled in the `.UI` and mark the parent root-only
(`kDataScaledSubtreeIds`) so its children are not scaled a second time. Both
cases absorbed several runtime workarounds first — hide/show, synthesized clicks,
per-frame re-apply — that half-worked; the data fix deleted the hack entirely.

### 2. Never scale these

- **Alignment markers** (`id=0x0000AAAA`) are positioning *data*. The game places
  a panel at `anchor − markerOffset` in native units, so scaling a marker
  displaces the whole panel by exactly that offset. True at runtime and in
  shipped data.
- **Font-sized and art-sized controls** (`kFontSizedIds`). A control sized from
  its rendered caption or from its own art is already correct once fonts and art
  are scaled; scaling again doubles it. Observed failures: a row twice as tall as
  it should be, and a spinner that overflowed its parent and lost its down arrow.
- **`cSC4WinAdviceList` children**, which the game sizes to the container.
- Never suppress paints to hide an open-flash. Pre-scale while the window is
  hidden instead.

### 3. Identify windows positively, never by size heuristic

Content-sized windows — tooltips above all — defeat any size range. Use an exact
width, a class plus id, or an explicit mode split.

### 4. State gates must be verified in all three city states

Pre-founding god mode, founded god mode, founded mayor mode. A gate that is right
in two states and wrong in the third is the most expensive bug class in this
engine. Founding a city makes several apparently hidden or inert windows go live,
which invalidates any note measured pre-founding.

### 5. One-shot captures are fragile

The Plot hook captures a strip's fields once; any other writer that runs first
poisons it. A sweep-side write captured 88 as the "natural" value, forced 176 on
top, and produced 4x pitch everywhere. Sweep-side code may **invalidate** a
capture, never write through it.

### 6. Skip lists written in an earlier phase rot silently

An id exclusion is a *claim* about the tree, and claims written before the tree
was understood go stale without saying so. The city sweep skipped `0xAA32BCE6`
for weeks under a label calling it plop-menu machinery; one dump read proves it
is the Data Views panel, which sat at 1x among a scaled HUD. When a subtree's
real owner becomes known, re-audit every skip that touches it.

Two corollaries, both proven twice:

- When one window id has several script copies, identify the live script by
  rect-matching a runtime dump, never by filename or guesswork.
- The lifecycle axis includes **expand**, and on panels carrying code-painted
  surfaces the untested state can be fatal rather than merely ugly. The Data
  Views fix was perfect in the compact state and crashed the game on expand. The
  expand path itself was innocent (pure show/hide); the killer was the map child
  `0x00004203`, a *second* `cSC4WinMiniMap` instance whose one-shot display
  surface stayed 256 while the renderer (`sub_7A2F60`) built window-sized
  buffers.

That yields two reusable rules. (a) Every `cSC4WinMiniMap` instance that gets
scaled needs the destroy-and-recreate surface lever; find instances by
`GetClassID 0x7A6580` = clsid `0xCA318388`, iid `0xCA318385`. (b) Code-managed
legends are re-laid on every view-select using 1x origin constants against
font-derived pitches that are already scaled, so the cure is a pin-back pass that
re-imposes the scaled design geometry each sweep while the panel is visible, with
targets measured rather than inferred. That panel is three coupled parts — sweep
plus art, the minimap recreate, and the pin-back pass — and breaking any one of
them regresses it.

### 7. A dangling `.UI` reference means the pixels arrive at runtime — find the binder, not the art

"Generate the missing scaled art" is a category error when the referenced TGI
exists in no shipped archive under any type. Prove absence with an any-type index
scan (`tools\dbpf\find_tgi.py`); a type-filtered extraction CSV cannot prove it.
The U-Drive-It picker cells' `{46a006b0,ea32f104}` is such a placeholder: binder
`0x76FDB0` calls SetImages with `{group 0x4C06F888, vehicle-exemplar prop
0xEBFC5E5E}` at runtime. The fix is to stage the whole runtime-bound group scaled
(collision-checked) and scale the placeholder `imagerect`s with it
(`RUNTIME_BOUND_2X` in `build_dialog_static.py`) — but only for scripts whose
runtime pixels really are that group. The Select-A-Sim picker shares the *same*
placeholder TGI yet receives runtime-generated portraits (`imagerect` 36x41 is
the tell) and needs the self-limiting BMPX destination hook instead: GZWinBMP's
Plot at `0x9BC325` draws `dst = src size` at the window origin and never reads
the window rect. Both builders classify and print `WARNING LEFT1X ... DANGLING`
versus `MISSING-2X`; those lines are meant to be read every build.

### 8. Same-project dats compete in the load order exactly like foreign mods

When an override mysteriously does not load, enumerate every shipped copy of that
TGI across the project's own dats first, with a Plugins-wide index scan. A
selective-art package that sorts alphabetically after the dialog package shipped
1x-geometry copies of the budget scripts and silently beat the scaled ones for
hours of debugging.

### 9. Every id in a runtime dialog list is non-unique until proven otherwise

A hidden template and the open instance share one id, so a first-match find plus
`IsVisible()` silently skips the real window; iterate all instances. Dialog
scaling must also preserve the centre and clamp on-screen — a 1000-wide modal
doubled in place put its buttons at x=2700, where they could not be clicked.

### 10. Identity is a content match, never a timing correlation

Ids picked from "what was open when the log line appeared" turned out to be the
advisor toasts, which then got doubled twice. Require a corpus root-id proof or
an executable builder proof.

### 11. Classify the window system before picking a mechanism

Run a depth-tracked top-level-root census of the script first. The budget is a
four-root *composed* panel (Graphs-class, children-only data double, plus
`kDataScaledSubtreeIds`); modelling it as modals, or as one docked panel, breaks
something different each time. Related: paint buffers are born at first-paint
size (`[win+0x6c]`), so a window swept after painting once at 1x keeps a clipped
buffer forever — born-scaled data is the fix.

### 12. Never stretch from a wide (>2048 px) tiled texture

Stock code only cell-copies from these; a stretched blit across tile addressing
splits and side-swaps the image, which is what mangled the gauge needle strips.
Ship scaled art so draws stay pure copies, and snap any hook multiplier to 1.0
for sources that are already scaled. Corollary: a positive vtable-slot check must
accept the mod's *own* other hooks in that slot — a paint-guard hook occupying
GZWinBMP's slot 88 made the BMPX hook silently never engage.

### 13. A code-created widget with a style PNG is born at the art's size

The executable's create helper (the `sub_77B960` pattern: parent, id, x, y,
styleTGI) sizes the window from its style PNG. Widgets whose style art ships
scaled therefore come out scaled with no other treatment — budget rows built from
strip `140155B7` go 1320x18 → 2640x36. A widget still at 1x inside an otherwise
correct dialog is either an explicit `SetSize(w,h)` constant in the executable
(patch the builder immediates; `CodePatches::ApplyBudgetButtonScale` covers 35
verified sites) or art deliberately left at 1x. Shared glyphs — slider
`46A006A7`, spinner `82B99D9D` — resize game-wide, so census their consumers
before doubling them. Frames that content-fit from font metrics self-scale and
must not be runtime-scaled on top.

Hard corollary: **a size or width guard cannot gate a repopulating window,
because the scale record outlives the state that matched it.** The
record-owning child pass then doubles whatever the game lays into the same window
later. The shared budget transient `0x0423278F` is banned from `kCityDialogIds`
in every form. Transient ids are non-unique *in time*, not only in the tree.

### 14. Before correcting a window the game just placed, check that the game was wrong

The quit confirmation jumped 213px on the first open of each session and was
perfect afterwards. The defect was not the game's placement but the corrective
move applied on top of it; opens after the first only looked right because they
inherited the moved position — an uninitialised latch, where later opens are
pre-warmed rather than faster. Read out of the executable rather than inferred,
SC4 places modal dialogs at `x=(W-w)/2` (`0x0078E409`) and `y=(H-h)/3`
(`0x0078E3DF`), deliberately a little above centre; confirmed against three
measured births (h=162→479, 175→475, 324→425). Once the dialog was born at its
true size the game placed it correctly on its own, and the cure was to delete the
centring, not to make it faster. A first-open jump is as likely to be a
correction as the game's error. Corollary: when something must be positioned,
match the game's own rule so the born path and the runtime path cannot disagree.

### 15. An override built from another mod's data must be gated on that mod

Otherwise uninstalling the mod does not uninstall the override, which lives in a
`zzz-` prefixed folder and outranks everything. The dependency table
(`ScaleTier::kThirdPartyDeps`) is the mechanism.

### 16. Born-scaling takes a window off the sweep, so it inherits everything the sweep was quietly doing for it

Marking a container born makes `Classify` return `AlreadyScaled`, and the sweep
then skips the **whole subtree**. Strip item metrics that had been scaled all
along silently stopped, leaving an 88x578 strip window full of 44px cells. Before
born-scaling anything, enumerate what the sweep currently does to that subtree —
geometry, child rects, control fields, hook installs — and take on all of it.

### 17. Prime a shared latch from a stock value; never let it see a scaled one

`SlotThunk2<88>` latches its 1x base from a strip's own fields on the first Plot,
then writes `base*f` forever — and the strip base globals are shared by every
strip in the game. Writing an already-scaled 88 into those fields at birth made
it latch 88 and emit 176, doubling every picker cell so both art states showed
side by side, game-wide. The cure is never "stop scaling"; it is to prime the
latch from the builder's own stock argument so it cannot see a scaled value.
Corollary: before writing any field an existing hook also reads, find the hook,
read what it does with that field, and check whether the global is shared.

### 18. A late hook install leaves a stale frame — cure it with one forced repaint, not a faster install

A scroll arrow reported "missing on first open, appears after you scroll" was
never missing; it was **unpainted**. The window painted its first frame before
the vtable swaps were in, and nothing asked it to paint again — scrolling was a
hand-triggered repaint. Force one invalidate at the instant the state goes live.
This is a forced repaint, not paint suppression, which blanks windows and is
permanently banned. Latch it one-shot per window: the block that does it can run
on every sweep tick, measured at 809 times in one session.

### 19. Match ini keys exactly, never by substring

A guard testing for `"BornScale"` matched the existing `SubBornScale` key, so a
kill-switch write silently did nothing while the path stayed enabled and was
reported off. Anchor the match: `^\s*KEY\s*=`.

### 20. A family that still misbehaves though "that was fixed" is on an older mechanism generation

The scaling mechanisms went through seven generations — scale-when-visible,
pre-scale-hidden, data pre-scale, builder constant patch, born-at-Place, born
chrome state, and data-born plus dependency gate — and a family fixed under an
early one is not revisited when a better one lands. One flyout, the first ever
scaled, sat on generation 1 for 28 versions while every sibling was upgraded
twice, and its notes still said "unsolved". Before designing anything, look up
the family's generation and the one cheap measurement that confirms it.
Corollary, and the reason this is expensive: **the older the note, the more
confidently wrong it is** — that audit found five stale claims still being quoted
as fact, including one about a *different* window being used to justify a gate on
this one.

### 21. A stale frame that survives a forced repaint is a stale *decision*

Law 18's repaint cure was shipped against a missing scroll arrow and cured
nothing, because the draw only reads flags (`[0x118]`/`[0x119]`, born 0) that an
open-time decision computes. Scrolling was not triggering a repaint; it was
recomputing the decision. The decision had mixed units: a born-scaled strip
window divided by a still-1x item pitch reads as "nothing to scroll".

Cure: **a born rect requires born metrics.** Write the strip's `0xF4/F8/FC` to
`base×f` at birth, after Place, with the latches already primed from stock (law
17), behind a read-guard that refuses unless the fields still hold the exact
stock values. Two corollaries measured the same night:

- A dock cache must be warmable **before** the first open — warm it from the
  persistent anchor (the toolbar) on every sweep tick, never from the transient
  window. A latch that can only warm while the flyout is open is cold on the
  first open by construction.
- A corrective move is not the same as born docked when part of the assembly is
  **parentless**: the disaster strip does not follow a container move, and only
  the game's own layout places it, which runs at open or on hover.

Offline proof pattern: emulate the three states (stock, half-born, born) and
assert the decision flips only in the half-born one.

Frame corollary, found by the read-guard itself: **a field offset derived from
disassembly must state its frame.** That strip has two — object-relative
`0xF8/0xFC/0x100` (`SetItemMetrics`' `self`, vptr at +0, what birth writes) and
window-relative `0xF4/F8/FC` (the Plot's `this`, the `cIGZWin` embedded at +4).
Writing the window frame's offsets on the object made the read-guard refuse on
every open and log `metrics left to Plot` rather than corrupt a field. When two
code sites disagree by exactly 4, they are probably both right in different
frames.

### 22. A source comment is an instrument with a scope — audit it like one

A comment claiming "the seven call sites" gated a whole design; an exhaustive
`E8 rel32` scan found **eleven**, plus a byte-identical twin opener
(`sub_7E5D80`) carrying two more. Three flyouts were wrongly filed as generation
1 on that comment's authority, and the one real generation-1 flyout — reached
through the unhooked twin — was invisible to it. The comment answered "which
sites were enumerated", not "which sites exist". When a coverage claim in a
comment gates a design, re-derive it from the executable; the scan takes minutes.
The same audit found two id-list comments swapped for weeks and a dock flag that
defaults to 0 with no shipped ini setting it.

### 23. Scoping a guard to the case you tested leaves the untested cases unguarded — and a state test must test the state, not a proxy for it

Two mistakes in one guard. First, an "already scaled, leave it alone" guard was
narrowed to the two ids one session had tested, explicitly documenting the others
as uncovered — and the save flow reuses one of those windows, so it arrived
data-born and was scaled again, measured as `0xAA8DEF97 (200,241 2000x700)`,
exactly 4x its 500x175 design. The `newW > scrW` bail cannot catch that (2000 <
2400). **Blast-radius caution applies to changes that act; it does not apply to a
guard that only ever declines to act, where narrowing adds risk.** Second, the
guard's test was `w >= designW*5/4`, true both of a window that arrived scaled
*and* of one scaled a tick earlier — which would have dead-coded the per-sweep
child pass for the whole table and poisoned a once-per-id instrument. The real
predicate is "is there a scale record?": hoist `Classify` and require `Fresh`.

Both were caught by adversarial review *after* an on-screen confirmation, which
is the point: **an eyes-on check confirms the pixels in one state; it cannot see
a later-sweep or other-dialog regression.** That same review also predicted a
failure the screenshot refuted, citing a note that predated the family becoming
data-born — refuters inherit stale notes too, so adjudicate their claims against
measurement like any other.

### 24. Before calling two of your own lists contradictory, check what each predicate is actually consulted by

Three ids sat in both `kNeverScaleIds` and `kCityDialogIds`, which reads like a
structural defect and is not. `IsNeverScaleId` is honoured **only** by
`ScaleOnShow` (dormant at the shipped hook default) and by the city sweep's
direct-children loop — not by `ScaleSubtree`, so membership never protects
against recursive descent. The list means "never scaled *by the sweep*", and the
dialog block is a separate mechanism for main-window transients the sweep cannot
reach. Two compatible statements about one window, read as a contradiction
because the name overstates the scope.

The reflex tidy-up would have deleted a safety net: measurement showed all three
ids are data-born at every scaled tier, so the dialog block's scaling of them is
unreachable in any shipping configuration — belt and braces against a
package-load failure. The fix was documentation plus a self-maintaining assertion
(a one-shot log naming the overlap, which changes if someone adds a new id), not
an edit. General form: **a list's name is a claim about scope; verify it against
the call sites, and prefer making a surprise self-explaining over removing it.**
The same mapping work proved that no width threshold works where the 1x and
scaled candidate sets overlap — the robust guard is an exact product match
against measured per-id 1x bases.

### 25. Law 13 has a converse: an explicit size after a clone beats the style PNG

A code-created widget is born at the art's size **only when the creator does not
size it explicitly**. With an explicit `SetSize`/`SetArea` after the clone,
scaled art is simply `fill=yes`-downscaled into the 1x window and nothing visibly
changes. A news-row dismiss control proved it: template script area 100x100, live
clone about 20px, i.e. code-sized. Check for the explicit size *before* shipping
art. If the live size matches neither the art nor the script, the creator sizes
it and the lever is the sizing constant, with scaled art as a prerequisite rather
than the cure. Extra trap: advice-list row furniture sits inside the no-recurse
subtree (`kAdviceListScaleSelfIds`), unreachable by every scaling pass by design,
so "why is only this child 1x" on an advice list always resolves to a code-side
lever.

### 26. A test that does the mechanism's job by hand cannot fail

A mod-removed test script moved both the mod's file *and* the override, which is
exactly what the dependency gate is supposed to do — so it verified rendering
only and never exercised the gate. A `-GateOnly` mode that moves only the mod
proved the gate fires on the same launch (the static-layer sync runs in
`PreAppInit`, before the plugin scan) and immediately caught a 4x dialog shipped
an hour earlier. **If the test performs the step under test, it is a rendering
test wearing a gate test's name.**

The defect it found was law 23's third strike, inside law 23's own fix: each
confirm id was given the single base its script was believed to own, the
script-to-id mapping was swapped, and the exact-match guard therefore matched
nothing and re-scaled a data-born dialog (`0xAA921F4F scaled (540x322) ->
1080x644`). Cure: **three candidate bases per id, every family member carrying
all of them**, so the mapping stops mattering — verified safe by arithmetic, in
that the products never collide with any 1x base at 1.5x, 2x or 3x. Corollary: an
exact-match guard fails loudly on bad data where a threshold would have
accidentally succeeded, which argues for completing the data rather than
loosening the guard.

### 27. When scaling one element deletes a different one, they share a width budget

Every advice row is a three-column HTML table whose total is the hard constant
`GetW() - 61` (`83 EE 3D` at `0x0079388F`; 61 = 18 + 18 + a flat 25 reserve).
Scaled arrow art grows the arrow column by 18, eats the reserve, and carries the
last column past the pane's content edge — so a dismiss control disappeared
because of the *arrow*. Reverting the four dismiss glyphs to 1x changed nothing,
and that null was read for a day as "the control's size is not the cause, so
there are no levers left", when it was actually the diagnostic that named the
arrow. Cure: re-derive the shared constant from the art, `round(18f) + 43`,
restoring the confirmed-good declared total rather than budgeting the overflow.

Two habits this earns. (a) When art makes a *neighbour* vanish, look for the
constant that sums the parts, not for a property of the thing that vanished.
(b) Justify the new constant as *restoring a known-good total*, which survives
the parts of the chain that were never measured, where "budget the overflow" does
not. Coda: once the shared total is correct, scaling the *other* member is free,
because both forms declare the same total and it only redistributes width — an
early build held the dismiss glyph at stock on an encoding argument that was true
but too conservative. **When you decline to scale something for a stated reason,
re-check that reason after the mechanism is fully understood.** This is also the
first mechanism where the data half is unsafe alone: art without the patch
removes a working control, so the two ship and revert together and the ini switch
is not a safe revert.

### 28. The boundary is the content width, not `GetW()` — it moves per tier, and it moves when a scrollbar appears

Disassembled from `sub_9BCBC5` at `0x009BCBC5` and confirmed on screen: a text
pane's usable width is `GetW() - 2*gutter - scrollbarW`, gutter default **5**,
and **`scrollbarW` is fetched live** from the scrollbar's own `GetW()` (vt+`0x0C`
then vt+`0xA4`). Three consequences:

- Arithmetic that asks "does the content fit" against the raw window width is
  measuring the wrong edge — a row can be invisible while pane arithmetic says it
  is still 7px inside.
- **A "fixed" reserve usually decomposes.** The stock 25 is
  `2*gutter (10) + stock scrollbar cell (16)`, and only the scrollbar half
  scales, because `SetImage` sizes the bar as art width / 12 — the scaled bar
  really is 32px at 2x. Shipping a flat 25 was half the answer. Test: **does the
  general form reduce to the game's own constant at f=1?** If it does, the split
  is right, and that check is free.
- **A scrollbar that appears changes the boundary mid-session.** A collapsed list
  has no bar and passes with a wrong reserve; expand a row, the bar arrives, and
  the last column goes over. Any width budget on a scrollable surface must be
  eyes-on tested in both states, and unless shared code is going to be detoured,
  budget for the worst case unconditionally — no single flat value is correct in
  both.

### 29. In a union-rect container you cannot data-pre-scale *some* children — all or none

A container whose rect is the union of its children with no clamp grows when any
child is pre-scaled past the design frame, and an edge-anchored parent then drags
everything with it: the dock minimap ended up rendered *outside* the dock. And
"all" is not always available — pre-scaling the dock's whole subtree requires
`kDataScaledSubtreeIds`, which **stops the walk**, and the god/mayor flyout
docking runs inside that walk, so every flyout came unstuck. With both doors
shut, that container is runtime-scaled only. Before pre-scaling any child, ask
what computes the **parent's** rect.

### 30. A list can grant two powers; check both before joining it

`kDataScaledSubtreeIds` means "do not scale this" **and** "do not walk here"
(`ScalePanelRoot` returns early). The dock only ever needed the first, and taking
the second broke unrelated machinery living inside the recursion. Read the
consult sites, not the name.

### 31. Matching the solved family is step one; step two is the new host's own constraints

A corrupted-minimap symptom correctly matched the advisor-faces family, where
load-time damage is cured in data and never by a faster sweep — and applying that
cure broke the dock twice, because the *host* had a union rect and a docking
recursion the advisor strip does not. The union rect was already documented and
was read that same session without being applied. **The family tells you the
shape of the cure; the host tells you whether it fits.**

### 32. Probe first — a log-only build is almost free and kills theories cheaply

Of four theories in one session, the two builds that only logged each refuted a
theory and cost nothing; the two that changed behaviour each shipped a regression
that had to be found on screen. When a mechanism is not yet established, ship the
instrument, not the fix. Corollary: **a probe that fails is still a result** —
reading garbage through the wrong offset is how `[win+0x6c]` was identified as
the draw context and how the vtable slot list was found to be off by one.

### 33. An inference written down as a measurement will silently kill your next seven candidates

"The corruption is present before the sweep" was recorded in four documents as a
measured fact. It never was: its only evidence was a probe line reading
`vis=1 onscreen=1`, produced by an `IsVisible()` walk up the parent chain — no
rect test, no composition, no pixel. It proved the visibility *flags* were set and
nothing more. Worse, the conclusion had been attached to it by a theory that was
later refuted for that window — the argument died and the premise it produced
stayed in the file, where it became the decisive kill in six of seven later
candidates. Three defences: (a) when you write a fact, write the instrument beside
it and what that instrument can physically see; (b) when a theory dies, search for
the premises it introduced and kill them too; (c) if a constraint is doing a lot
of killing, re-derive it before trusting it.

### 34. A "safe" probe helper is only safe on the type it was written for

An SEH-wrapped buffer prober had been safe for years on COM buffers, so it was
pointed at `[+0x114]`, which is a plain `{pixel ptr, w, h}` struct.
`QueryInterface` is a virtual call, so it loaded the first pixel of the map raster
as a vtable pointer and called through it. SEH caught the fault, which is exactly
why it survived review and shipped. **`__try` makes a wild call survivable, not
correct** — and every value it returned was garbage being read as a measurement.
Check the type at the offset before reusing a prober.

### 35. When a repair is in the frame, check what the repair *destroys* before hunting for what corrupts

A dock minimap showed a wrong image on city open. Every theory asked what writes
the bad pixels — the message queue, scaled art in a 1x window, data pre-scale, a
stale private buffer, an uninitialised raster, the vtable. All six died. Nothing
wrote bad pixels: **the surface-recreate erased good ones.** The display surface
was destroyed, a new one built and pre-cleared to black, so the map vanished
until the engine's own bake landed and the empty box read as corruption. The cure
was to carry the old picture across the recreate — capture, recreate, black
floor, repaint bilinear — not to find a corruptor. **If your code touches the
thing that looks broken, put your own repair on the suspect list first; it is the
one candidate that never gets refuted, because nobody thinks to accuse it.**

### 36. Sample on a diagonal, and report a distinct count

A raster probe sampled `p[0]`, `p[n/4]`, `p[n/2]`, `p[n-1]`; for a 64-wide buffer
`n/4` and `n/2` are exact multiples of the width, so three of four samples landed
on column 0, all border. Four identical greys came back and were read as "the
buffer is blank", which is not what they showed. **Any sample stride that shares
a factor with the row pitch degenerates to one column.** Sample a diagonal
through the centre, and have the instrument report how many *distinct* values it
saw so the answer does not depend on eyeballing hex.

### 37. "Smaller than the thing that was banned" is not a safety argument

The ban on geometry work inside `PostCityInit` came from a 456-window full tree
walk. Reasoning that one subtree of about 25 windows was therefore safe produced a
crash on the first city open. The log proved the *quantitative* reasoning was
fine — `ScaleAll done, 431 windows`, exactly 25 fewer, so idempotence worked
perfectly — and that the *categorical* reasoning was wrong: two byte writes at
that site are safe and 25 geometry mutations are not. Writing a flag and re-laying
a window are different kinds of act, and scaling one down does not make it the
other. When a ban's stated reason is a quantity, ask what the quantity was a proxy
*for* before assuming a smaller dose is safe.

### 38. A live escape hatch is not a safe default

That same crashing mode shipped as the *compiled default*, with an ini key as its
guard. That protects only the machine whose ini was already edited and would have
crashed every other install. **If the only thing between a player and a crash is a
line in a config they did not write, the default is wrong.** Ship the unproven
mode off and let the ini turn it on, never the reverse.

### 39. The born-correct lever for city-load panels is the `SetFlag` detour plus a design-child-count gate

Three families of load-tail mechanism, one line each: the *message queue* never
fires during the load tail; *geometry inside `PostCityInit`* crashes; but the
`SetFlag` detour runs on the game's own stack and keeps firing after init
returns. So gate on the subtree reporting its **full design child count** — the
direct "fully built" signal; a consecutive-checks stability test costs about
625ms because `SetFlag` is scarce during load — and scale there. Measured
+328ms and +109ms against the sweep's +968ms. Two corollaries that made it work:
(a) if the subtree owns a one-shot surface, scale and recreate are **one action**,
and splitting them produced a heap-overrun crash; (b) route through the sweep's
own `ScalePanelRoot` so the scale map makes the later sweep a no-op instead of a
second doubling.

### 40. Every built package gets a deploy line and a hash pair in the same change — equal sizes prove nothing

A package that was never added to the deploy script froze its deployed copy at an
old epoch while the art classification moved on from shared to exclusive, leaving
clone references dangling and five radio rows drawing as bare fill-colour bars.
The stale and fresh dats had **identical byte sizes and identical entry counts**,
because a reference rewrite swaps equal-length hex, so every existing check was
structurally blind. The guard is a deployed-equals-built content-hash section in
the integrity test. Corollary from the same A/B: a stock-compare staging script
must disable **every** layer the project owns, `zzz-` subfolder included, or the
"stock" capture silently keeps mod data live on the exact panel being measured.

### 41. An installed hook is not an executed hook — count calls, not installs

A GZWinBMP draw override reported `25 instance(s) hooked` on the failing open —
true, and it read as "this panel is covered" — while the engine painted those
cells through a path that never calls the per-window Draw, for 13 seconds on
screen. Every earlier theory died because they all assumed the hook ran. The
instrument that solved it counts **calls per user-visible event**, a per-open
census of counts, which cannot saturate the way a log-line budget does, so a
failing event is guaranteed to leave a line saying so. Corollaries: (a) invalidate
the **leaf** that was hooked, not just its root, because the root's dirty flag
does not reach the leaves' draw path (measured: root-only is "less frequent but
still happening"); (b) intermittency in a draw defect usually means **two paint
paths**, not randomness — find which one runs when it looks right.

### 42. An offline gate is only as honest as its scope — state the scope

A Python model of the game's own `sub_79AD00` matched the real machine code
**32/32 exact** across 8 item counts and 4 scale factors, clamps included. It was
right — about the *container*. The emulator does not model the ring blit, so
moving the container slid the ring off its button by exactly the distance moved,
visible instantly on screen. The pass was real and the conclusion was wrong,
because nothing recorded what the harness does **not** cover. Corollaries: (a)
before trusting a gate, name the parts of the system it omits, and if an omitted
part is coupled to the part being changed, the gate cannot clear the change; (b)
the coupling was already recorded in the mod's own source ("origin stays put …
scaling it undocked the circle") — search the thing you are about to move for the
word that describes its partner; (c) a 197px measured error is a real finding even
when the fix built on it is wrong: keep the measurement, revert the behaviour.

### 43. A coupled pair ships together or not at all — and the second half is usually already in hand

When two quantities are welded by a latch, changing one is not progress toward
the fix, it *is* the bug: moving a flyout container to the game's own clamped
position was correct and validated, and it slid the ring off its button, so it
was reverted the same day. The missing half turned out to be a lever already
recorded live for seven versions (the ring blit Y) plus an offset already applied
at blit time (the ring delta Y). Corollaries:

- Before building the second half, spend one command proving the mechanism — four
  field-dump runs converted a high-confidence inference into a measurement for
  free, and the honest label "inference, not a byte-read" is what got that test
  run at all.
- Pin the half you are *not* fixing to its measured-correct current value rather
  than re-deriving it. The derivation may use a different convention: the game's
  own X anchor draws the ring 13f right of the button centre while the mod centres
  it — both "right", 26px apart, and swapping conventions mid-fix silently
  desyncs the birth path from the sweep.
- **Whatever moves a sprite must also move its hit box.** A relocated ring with a
  stationary back-arrow zone is a regression no screenshot shows.
- A gate for the second half must be able to *fail* on the first half's code, or
  it is decoration.

### 44. A probe for a fix must adjudicate the fix, not just sight the target

Shipping insurance for something never observed leaves you unable to tell inert
from broken, so make the probe print the verdict, not the sighting. A probe
written to say `463x132 means still 1x - insurance did NOT take` versus
`born/scaled 2x (insured)` reported the failure on its first outing: the data half
had scaled the child while the root stayed 1x, because the city sweep skips
`vis=0` windows and only `kAlwaysScaleCityIds` grants the visibility exception. A
sighting-only probe would have printed "found it" and left a scaled-child-in-a-1x
-root state shipping indefinitely, looking fixed. Corollaries: (a) the same line
should carry the facts that decide the next move — parent id, sibling versus
child, visibility — so one appearance closes the question; (b) when a task's
premise is a question, let the probe test the premise too (the answer here was
"no vehicle spawns it — it is resident and hidden", which no amount of
vehicle-cycling would have produced); (c) put the probe in *before* the fix is
confirmed, because its value is highest exactly when you believe you are done.

### 45. If the generator's output is not the shippable file, the generator's output will eventually ship

Two font styles were hand-added to a candidate ini *after* generation, so
`make_fontstyle.py <factor> <out.ini>` — the exact documented command — produced a
file missing them, and the DLL's popup retarget then pointed at styles that did
not exist at 1.5x and 3x. It degraded softly, i.e. failed invisibly, and shipped
that way for five weeks; anyone following the docs produced the broken file.
Corollaries: (a) make the generator emit the hand-added part and fail hard if its
own output lacks it; (b) upgrade the self-check from "the computed values are
right" to **byte-identical to the known-good artifact** — the old size-only check
passed happily while two whole styles were absent; (c) the asset family with no
deploy automation and no content assertion is the one that has already rotted;
(d) a generator that writes to whatever path it is given will happily fill a
*source* directory with intermediates that someone later deploys, so regenerate
every copy or the stale one is a loaded gun.

### 46. Prove the repaint before you tune the value

On a code-painted control that renders into its own cached buffer, every
field-level fix looks identical to no fix at all, so tuning values first burns a
build per hypothesis and teaches nothing. Three attempts on the Graphs chart all
"worked" by their own logs — the sentinel re-arm re-laid the rect, the font change
applied, the direct rect write stuck and was still there three ticks later — and
the screen never moved. Corollaries: (a) first establish that the thing re-renders
when poked, by changing something guaranteed visible such as a fill colour or an
obviously wrong rect, and only then hunt the right value; (b)
`InvalidateSelfAndParents` is **not** proof of a repaint for this class — the
established lever is the buffer force-recreate (`SlotThunk<88>` plus the
force-recreate flag), the same one the sub-flyout and the gauge dials needed; (c)
"the field holds the value that was written" is a *write* confirmation, never a *render*
confirmation; (d) when N different levers all produce zero visual change, stop
trying levers — the common factor is downstream of all of them.

### 47. A control that draws right but does not respond: check whether your own geometry pushed it outside an *ancestor's* rect

Sprite and hit box are the same rect on this engine —
`SetW`/`SetH`/`SetSize`/`GZWinMoveTo` all funnel into `SetArea` →
`CalcAbsoluteArea` → `[this+0x14]` — and concluding from that that "draws right,
click dead" cannot be geometric is wrong, and cost a not-a-bug closure on a real
defect. The rects agree, but the router's hit walk descends only into children
whose rect **contains the point**, so a child that is perfectly self-consistent is
still unreachable if any ancestor no longer covers it. The engine does not clip
the draw, so it keeps painting in the old place and looks fine.

A worked instance: a pin gave an empty-ledger popup its twin's stock height (125
against its own 100). Its host *is* the box — a top-level 600x127 window, 127 only
because the patch hits the `push imm8` ceiling — so the pin's own y clamp resolved
to `127 − 250 = −123` and put the close control at host-local y=−101, above the
host. It was logged **19 times** as `POPBOX 600x127 -> 600x250 at y=-123` and read
past every time, because nothing said a negative y was pathological. Corollaries:

- **When you resize a window, ask what its parent is.** If the host is itself a
  box sized by the same patched constants, growing the child alone is guaranteed
  to displace it. Move the whole set or none.
- **A clamp that can go negative is a bug detector you already own** — assert it,
  or it silently relocates things.
- **A twin pair must each reduce to its own stock value at f=1.** Sharing one
  constant across two builders is how a correct fix becomes a wrong one.
- **The stock control settles it in two minutes and needs no build.** Stage stock,
  click the thing: if it works in stock, the defect belongs to the mod, and no
  amount of disassembly outranks that.

### 48. A gate can be right about its bytes and wrong about the question

A gate decoded a budget dialog's command dispatch correctly and passed a real
positive control — then was quoted for "the close control cannot close the box",
which it never tested. Nobody established that a *click* on that control arrives
at `sub_78B120` as command `0xCC`; it does not. The positive control only proved
the classifier could recognise a close idiom, not that the handler is the path a
mouse click takes. **Before quoting any gate, state the step that connects its
subject to the observed symptom — and if that step is untested, the verdict is
UNDETERMINED, not proven.**

### 49. Wasteful-looking code is load-bearing until the comment says otherwise, and the optimisation you want is usually already measured

Five loops in `UiSpike.cpp` re-enumerated a whole child list once *per child*, on
a 16 ms tick. The obvious fix — hoist the enumeration out of the loop — is wrong,
and the site's own comment says why: the list is re-read because the mod's own
writes can make the game destroy a later sibling, so a pre-loop snapshot is stale
by construction and the crash returns under rapid menu switching.

- **The sound change is conditional, not removal**: re-verify only when the
  previous iteration actually mutated something. Nothing else runs in the stack
  frame — single UI thread, and this code never pumps messages.
- **Prefer an existing counter over a new flag.** The plan called for a fresh
  `mutatedSincePrevVerify` set at every mutation site, with the warning that a
  missed one reintroduces the crash silently. Auditing first showed `count`
  already *was* that flag: every `SetW`/`SetH`/`GZWinMoveTo` is paired with a
  `count++`, and it has to be, because `count` is the number the
  `"%d windows scaled"` log lines are read from. A new flag can silently miss a
  site; this one cannot without breaking an instrument dozens of fixes depend on.
  When you need "did anything change?", look for a number the code already
  maintains and that something else already checks.
- **Grep direction is a real trap**: searching for `count++` *after* each mutation
  found nothing at the third cluster and nearly produced "this path does not
  count" — the increment sits *before* the writes.
- Write the refutation at the site; a do-not-hoist note now guards it.

### 49A. The counter was right and the re-baseline was the bug

Law 49's fix shipped with a use-after-free that only adversarial review caught,
where the independent refuter tried to kill the finding and instead produced the
minimal fix.

- **A verify proves liveness of one pointer, never of the remainder.** The gate
  re-baselined its mutation signal whenever a verify ran, crediting every later
  index with a check that looked up only the current one. Kill sequence: i=0
  mutates and the game tears down c1 and c2; i=1 verifies (c1 dead, continue) and
  consumes the signal; i=2 skips its verify and dereferences freed c2. Fix: delete
  the mid-loop re-baselines, take the baseline once before the loop. The only
  sound skip window is the provably-safe prefix before the **first** mutation —
  and the steady state still costs zero enumerations, which is where the whole
  O(n²) win lived. **When optimising a safety check, the only sound skip is one
  you can prove from a state the checked object was known good in.**
- **"Verified zero mutations inside the block" was a null with no positive
  control.** The scan's regex matched `Set*`/`GZWinMoveTo` *calls*, while the
  block's real mutations were raw vtable swaps (`*(void***)w = gVtCopy`), a flag
  write, and invalidations. It gated a draw-hook re-find off and the regression
  was reachable in the shipped configuration. A mutation scan must enumerate
  mutation *mechanisms* — calls, vtable stores, flag writes, invalidations — and
  must first prove it can see each one.
- Adversarial review of fresh changes is not optional at these stakes: 46 findings
  raised against one build, 38 refuted, 8 real, including one crash and one
  reachable behaviour regression. The refuters killed most of the noise and
  sharpened the real findings.

### 50. A documented setting that does nothing is a lie, and it needs a gate

Three keys in the shipped ini (`Scaling/AutoConfig`, `PresentWidth`, `PresentHeight`)
were parsed into settings and then read by nothing at all. A player could set
them, see no change, and have no way to distinguish a wrong value from a dead key
— the ini is an instrument and it was lying.

- The shipped ini documents **only** keys the code reads; everything else falls
  back to code defaults, and absent is the supported configuration.
- `_tests\Test-ShippingIniKeys.py` enforces that, checks for a BOM, and asserts a
  positive control — which caught its own false failure on `ScaleFactor`, read
  through a `GetPrivateProfileFloat` helper with no trailing `W`. **The first
  version of a consistency gate is usually wrong about the code, not about the
  data: make it prove it can fail before you trust a pass.**
- Same family as silent truncation caps and law 42: each is an instrument that
  reports success while never having looked.

### 51. When the game refuses to do something, find the one instruction that refuses — do not paint over it

The Data Views map drew data cells on black at 2x on small tiles. Five
pixel-level cures were built and all failed: a one-shot seed (wiped by the game's
roughly 1 Hz re-clear), a 30-sweep heal whose black test compared against numeric
0 when the game's black is `0xFF000000`, so it had never fired, a per-sweep cached
heal that produced wrong cell colours, and a size clamp that was correct but shrank
the map.

- **The killer fact was compositing order**: the game clears, bakes, then
  *alpha-blends* cells onto whatever base exists. With a black base the cells are
  born dark and no later repair can un-blend them. When a fix has to run after the
  thing it fixes, ask whether the damage is already baked in.
- **The real cause was one unsigned compare.**
  `0x7A8560 lea ecx,[edx+2]; cmp ecx,4; ja skip; jmp [ecx*4+0x7A8628]` is a
  5-entry blitter table indexed `zoom+2`, so `zoom=-3` wrapped to `0xFFFFFFFF` and
  skipped the tile. The destination math on either side was fully general.
  Fifteen bytes re-pointed at a 6-entry table — entry 0 the mod's, 1..5 the game's
  own stubs — fixed it completely.
- **The disassembly should have been step 1, not step 10.** About 13 builds were
  spent guessing against what was on screen; the disassembly answered it in one
  pass. If two successive fixes in the same area fail, stop shipping and go read
  the code that is refusing you.
- A recompute that marks dirty is not a paint. The paint was message-driven and
  landed after the panel was visible; calling the game's own bake synchronously
  while hidden removed the last jump.

### 52. A fallback you did not retire is a bug with a polite name

After the real fix landed, the map still jumped on open, because the old
dock-seed workaround still fired and overwrote the correctly baked terrain with a
blurry upscale: good map, worse map, re-bake. The header comment already said the
seed and heal "are fallbacks that must stand down when this is true" — and **the
condition had never been wired**. A comment describing code that does not exist is
the same defect as a lying log line.

- When a real fix replaces a workaround, gate the workaround off in the same
  commit and prove it with a log census; the acceptance evidence here was
  `SEEDED 0 / probes 0 / HEALED 0 / CLAMPED 0 / faults 0` alongside
  `x8bake=live blits=16 clips=0`.
- Keep the workaround as an explicitly gated fallback for when the real fix
  declines (wrong executable build, another mod owns the site) — but the gate must
  be a live expression, never a sentence in a comment.
- The stock control decided that session twice, both times against the stated
  expectation: the black map was the mod's, and so was the open-jump. Two minutes,
  no build, each time.

### 53. Extrapolate a tuned correction the way the thing it corrects is placed

The disaster ring's delta X and Y are a correction over the game's 1x ring-blit
anchor, hand-tuned at f=2. Carrying them to other tiers by scaling by **(f−1)**
asserts that the correction is zero at f=1. It is not: the 1x anchor is the
**undocked** seat, and the ring only sits on the button after the **dock** runs,
which is itself a scaled placement with every term proportional to f. The docked
seat therefore scales linearly, the (f−1) law drifted, and at 3x it parked the
ring 8px right and 7px low. Cure: **seat-scaling** — keep the sprite's centre at
its f=2 docked seat scaled by f/2 and subtract the scaled half-size. Bit-identical
at f=2, so the tuned tier cannot regress.

- Before choosing (f−1) versus f, ask **what state the f=1 value describes**. An
  (f−1) law is sound only when f=1 is the same state you tuned in.
- 2x is a blind spot for tier math, because both laws agree there. **A tier
  extrapolation is unproven until a third tier has seen it** — and fixing one tier
  silently moves the others.
- A tier fix ships with its own re-verify obligation named, per tier.

### 54. A fix that produces no log line did not run — stop re-deriving the value

One defect cost two builds proving the same arithmetic twice. The first attempt
sat inside the anchor block, where the child is anchored before its anchor sibling
and only once, so the guard was always false; the second sat in the load-time
sweep, and the panel only exists once it is opened. Both times nothing moved on
screen and the log had zero instances of the fix's own log line. That absence
**was** the diagnosis, and it was read as noise twice.

- When a fix has no visible effect, the first question is **"did this code run?"**,
  never "is the value right?". Put a named log line on the write path.
- Absence of that line is a measurement, not a null: it needs no control, because
  the line is emitted unconditionally on the path being tested.
- Ask **which pass and which order** before writing a placement fix — load-time
  sweep, per-tick incremental, or the show hook. A user-openable panel does not
  exist during the load sweep.

### 55. Dock relationships belong in a table

Every panel positioned relative to another gets a row — `{child, anchor, offX,
offY}` — and never bespoke code. A per-panel anchor that places each root from its
*own* design gaps is right for a screen-edge dock and wrong for a sibling pair,
because the game's native seat between the two differs by resolution and per-panel
scaling multiplies that drift by f: measured 1px apart at 2400x1600, 7px at
3840x2160, which projects to 21px at 3x.

- **The offset law:** measure the offset in the anchor's scaled pixels at the
  confirmed f=2 tier and apply it as `offset * (f/2)`. Identity at 2x by
  construction, so no tier needs a special case.
- The table pays for itself immediately: making docking born-correct took one
  predicate, and every present and future row inherited it.

### 56. Prefer a fix that self-gates on the defect over one that gates on a tier

A rating-arrow detour compares the live position against the game's cached seat
and writes only when they differ, computing no coordinates of its own — it writes
the game's own cached value back. That is what made extending it from 3x to 2x
safe as an *argument* rather than an assurance: a correctly seated arrow has live
equal to cached, so there is nothing to write. A tier gate protects the confirmed
tier by never running; a defect gate protects it by having nothing to do. Only the
second generalises. Corollary: when a tier gate widens, its justifying comment
goes stale in the same edit — fix it in the same commit.

### 57. A fix that must re-apply every tick is a fight, not a fix

If the object being changed is owned by a rebuild, change it **inside** that
rebuild. Resizing region tile buffers from the mod's own tick worked (9 of 9) and
the game restored them every frame — the counter climbed 9/18/27/36 unbounded,
nothing changed on screen, and clicking broke because a sibling buffer built
during the rebuild went stale. Hooking the builder (`sub_7AE3D0`) fixed all of it
at once, because every downstream step then inherits the new size. Acceptance
criterion: **the counter must stop climbing**, verified in the log before the
build is ever seen on screen.

### 58. When a subsystem resists two attempts, decompile the module

One defect cost five builds guessing one address at a time from prior reports; the
whole region screen was 197 functions and 52KB, and one fan-out decompiled all of
it. The fix landed on the next build. Three existing claims were wrong and only
the bytes caught them: the vtable slot (right all along), the argument count (four
dwords plus `ret 0x10`, where three plus a pointer were being passed), and which
buffer set the on-screen rect. It is cheaper to read the module once than to infer
it seven times.

### 59. Every consumer of a shared hook needs its own gate, and an anchor's lifetime is part of the dock

- **The eye-measured offset.** A dock table anchored the Graphs radio band to the
  chart's *top* by a delta read off a screenshot (+640). The `.UI` design is
  bottom-referenced. Proven by diffing the two scripts that share band id
  `0x0A4A8176` — Graphs `I-6bc9065a` against Data Views `I-ea2871aa`, the panel
  that rendered correctly. **A wrong relationship scaled faithfully is wrong at
  every tier**, which is why it reproduced identically at 2x and 3x and why no
  tier math ever found it. When two panels share a widget id and one renders
  right, diff the designs: that is a free controlled experiment.
- **An anchor's lifetime is part of the dock.** The next build anchored to
  `0x8A8B5B72`: right arithmetic, wrong window. Measured from the log, it opens
  about 19s *after* its child, and the dock pass bails on
  `!pAnchor->IsVisible()`, so it could not dock until that window was opened by
  hand. Check *when* an anchor appears relative to its child, not only where it
  is.
- **The real one — law 41 again, and it hid two correct fixes.** A born-correct
  "dock at show" lived inside `ScaleOnShow`, which only runs at
  `gShowHookMode >= 2`. The shipped ini has `ShowHook=0` and the log says
  `SHOWHOOK installed ... (mode 0: log only)`. The dock-at-show had never executed
  once; the per-tick pass always cleaned up after the first paint, which is the
  one-frame jump. Two correct fixes shipped before anyone checked whether the path
  ran — and that same function already carried the warning for an earlier
  consumer ("the trampoline now serves two consumers … would silently never run if
  this still keyed off it alone"). Dock-at-show was the third consumer, still
  keyed off the wrong flag. **Before improving behaviour behind a hook, prove its
  branch executes: read the mode from the live ini and the "installed … (mode N)"
  line from the log, never the default in `Settings.h`.**
- A show detour fires on the 0→1 transition, so `IsVisible()` is still false for
  the very window being shown. A dock called from there must gate on **geometry**
  (`w/h > 0`), not on the visible flag, or the guard rejects precisely the case it
  exists to serve.
- Do not revive a refuted mechanism just to reach your code. Raising the show-hook
  mode would have run the dock, and scale-at-show is recorded as refuted for the
  city HUD. Give the new consumer its own gate instead.

### 60. The 1.5x tier signature is the null hypothesis, not evidence

"Broken at 1.5x, perfect at 2x and 3x" feels like a fingerprint. It is not:
`Upscale2x.cs::ScaleDim` returns early at an integer factor and `ScaleRound` is
exact there, so **every** arithmetic disagreement between two scalers is
1.5x-only by construction. Four separate theories matched that pattern perfectly
and all four were wrong. A candidate earns nothing for matching the tier pattern;
it must also survive a test that could have refuted it.

### 61. `GZWinBtn` stretches — a state cell need not match its window

Measured across all 281 scripts, the count of buttons whose cell width differs
from the edge-derived window width is **709 at 1.5x, 420 at 2x, 420 at 3x** — and
the integer tiers are confirmed correct on screen, with extremes like a 24x6 sheet
(cell 12) inside a 996-wide window. A cell/window mismatch is therefore normal
engine behaviour and may **never** on its own justify changing `ScaleDim` or
`ScaleSubtree`. Corollary: `ScaleDim`'s tie-break direction is nearly irrelevant
(ties-down 701 versus ties-up 709 of 868).

### 62. Build the instrument that can *see* the defect class, not another one that can only count

Every gate in the offline emulator directory was arithmetic — its own README says
it never looks at a pixel — so ten theories were checked against numbers instead
of against an image. A compositor (`tools\uimap\emu\render_flyout.py`: `imagerect`
crop, `sheetW/states` cell, magenta punched to alpha, 1:1 blit, green window
boxes, any tier, either geometry rule) then killed two theories in three minutes
each, offline, with no build and no launch. When a defect is about what something
*looks* like, render it.

### 63. A repair aimed at a symptom you cannot see will break something you can

An `imagerect` under-read was real arithmetic — 427 rects short at 1.5x, 0 at 2x
and 3x — and closing it damaged the thumbnail flyouts twice: a tolerance widened
small-atlas cells across two cells, and the exact 1x test then widened the last
cell of every strip, which legitimately ends at the sheet edge. Meanwhile the
reported defect never moved, because those buttons carry no `imagerect` at all.
**Before repairing a discrepancy, prove the thing you are trying to fix actually
reads the value you are changing.**

### 64. Go find the instance that has a sibling that works

"The sun and the moon are wrong" is consistent with a hundred mechanisms, and ten
of them survived a day of testing. "**One of these five identical buttons is
wrong**" is consistent with almost none, and named the cause in minutes: the five
Landscape buttons are identical 47x37 controls on identical 188x37 sheets, and the
broken one is the only one at an *odd* left edge (69 against 68). `ScaleSubtree`
is edge-derived — `newW = ScaleRound(l+w,f) - ScaleRound(l,f)`, deliberately, so
abutting siblings stay abutting — so at f=1.5 an odd `l` costs the window exactly
one pixel while the art cell keeps all 71. **When a defect resists, stop
instrumenting the broken instance and go hunting for a working sibling.** The pair
is the experiment; the broken one alone is only an anecdote.

Two more facts from the same defect:

- **`ScaleDim`'s cell unit is a guess.** It takes the LCM of every count in
  {2,3,4,6,8,12,16,24} that divides the width, so a 136px four-state sheet gets
  snapped on 8 and lands at 208 (cell 52) when its button wants 51 — and it snaps
  *heights*, which a horizontal strip never needs. The upscaler runs over a
  directory and cannot know the consumer; the builder parses the `.UI` and must
  not guess: `sheetW = states * ScaleRound(w*f)`, `sheetH = ScaleRound(h*f)`.
- **Regenerate from the 1x source, never resample the upscaled sheet.** Double
  resampling compounds the error and smears the magenta colour key — the same
  failure that shipped a pink Mayor Rating bar.

### 65. A fix that *moves* things is judged by its densest neighbourhood, not by the case that reported the bug

Moving 177 buttons onto an even edge fixed a reverse-L artefact and was worth up
to 2px at 1.5x. On the Landscape flyout — five buttons with 50px of air between
them — it was invisible. In the Sim-selection script (24 and 28 nudges, the most
of any script) twenty-one faces visibly slid inside their own frames, the advisors
went left and high, and the budget rows and bottom dock misaligned. **Before
shipping a positional change, find the tightest layout it touches and judge it
there.**

### 66. Editing geometry in a `.UI` has the scope of that `.UI`; editing *art* has the scope of the whole game

Regenerating 61 state-strip sheets at exactly `states * window` was arithmetically
right, took the offline mismatch count to 0, reported **0 conflicts**, and broke
the flyout thumbnails on hover — because **flyout strip items are created at
runtime and appear in no `.UI`** (item-create does `SetArea(0,0,GetW(),GetH())`),
yet they bind art **by TGI** like anything else. The conflict check could only
enumerate `.UI` consumers, so it was blind by construction. A `.UI` edit cannot
reach a window that is not in a `.UI`; an art edit reaches every consumer that
exists. **Do not change art dimensions until you have an instrument that can
enumerate the runtime consumers of a TGI.** Refuted in the same pass: "a stale
`imagerect` elsewhere describes the old size" — of 115 art-sized strips in scope,
zero carry an `imagerect`.

### 67. When the size is wrong, change the size — not the position, not the art

Because `ScaleSubtree` is edge-derived, the scaled *size* depends on the
*position*, and at f=1.5 an odd left edge costs exactly one pixel. The cure is to
take **leaf** windows (`GetChildCount() == 0`) size-derived, `ScaleRound(w,f)`:
nothing moves, the size changes by at most 1px, and the art cell finally matches.
Leaves only — a window with children is a panel whose edges are load-bearing,
which is what edge-derived is protecting, and white seams between panels are the
failure mode. No-op at an integer factor by construction, so 2x and 3x need no
re-proof.

### 68. Read the format off the shipped bytes before writing a record

An LTEXT header written as a hardcoded `0x0008` was correct only by luck: the
field is the **character count**, `size = 4 + 2*count` — `0F..` = 15 for
"Total Garbage\r\n", `0A..` = 10 for "Exported\r\n", `08..` = 8 for "Imported".
Dumping three real records also settled a judgement call for free: `Imported` is
the row directly above the new one in the same legend and carries no trailing
CRLF, so omitting it matches the row's own siblings instead of being a preference.
**The neighbouring record is both the format spec and the style guide.**

### 69. "This wasn't like this before" is a bisection boundary, not an opinion

Four defects — a face grid, the advisor portraits, the monthly budget rows, the
flyout thumbnails — were reported minutes after a deploy, so both of that deploy's
changes were reverted. **The reverts fixed nothing**, because the cause was a
change from eight hours earlier. The observation that the issues were absent at
the start of the 1.5x work was the better instrument: it named a bisection
boundary that the timing coincidence had hidden. Coincidence in time is not
causation. **When a revert does not move the symptom, the attribution was wrong —
stop reverting and go bisect.**

### 70. A "safe" over-approximation is still a change, and it is paid for in pixels

`Upscale2x.cs::CellUnit` snaps scaled dimensions to preserve the game's integer
cell divides, which is correct. It was then widened to **the LCM of every count in
{2,3,4,6,8,12,16,24} that divides the width**, on the reasoning that a bigger
common multiple makes *any* divide safe. It does — and it makes every sheet whose
width merely happens to divide by a large number bigger than its consumer's
window. A 200px four-state sheet got `LCM(2,4,8)=8`, so 300 — already a clean
multiple of 4 — was pushed to 304 and every cell came out a pixel too wide.

Measured over 255 art-sized four-state buttons (cell ≠ window), the count of
mismatches by choice of snap unit: `LCM{2,3,4,6,8,12,16,24}` **152** (the shipped
value, and the worst option except doing nothing) · `LCM{2,3,4}` 98 ·
**`LCM{3,4}` 34** (chosen) · `{4}` 19 (rejected: it drops the nine-slice `/3`) ·
no snap 104.

`{3,4}` keeps the two divides that are load-bearing — the nine-slice
`img->Width()/3` and the four-state `width/4` — and `/12` for the scrollbar falls
out as their LCM. For `.UI`-bound sheets the `/3` drawer is `GZWinBMP`'s edge
branch at `0x009BC325` (or `GZWinBtn` at `0x009B05E0`), which divides its own
source rect and then calls the blitter at `0x008D8800`; `0x00794100` is
`cSC4WinAlertBorder`'s own draw, a different job at a similar-looking address.
**LCM-of-everything is safe against cutting and unsafe against fitting — measure
the overshoot before choosing a wider constraint.**

### 71. A gate that only asks about your own work cannot see work you never started

A third-party mod's info screen rendered at 1x under 1.5x fonts for the entire
life of the project, with every offline gate green, because every gate asked "is
the built output still correct?" and that dialog was never built. The dialog
builder's winner assert even asks the adjacent question — "has a mod taken over
one of the project’s own targets?" — and had never asked its mirror, "is a mod's *own* dialog
scaled at all?". **Run the census in both directions: enumerate what exists and
subtract what is handled.** The instrument already existed and had been reporting
the three unhandled scripts under a heading called "What to do" since the day it
was written: a correct report nobody read.

### 72. `blttype=normal` art is clipped by its window, never stretched to it

So art and window cannot be the same size at a fractional factor, and must not be
made so. A 285px strip upscales to 429 (a cell unit of 3 snaps 427.5 up) while its
window is edge-derived to 427 **or** 428 depending on the parity of its left edge
— two windows in the same dialog, one bitmap. The overhang is structural, not a
defect. A first gate asserting "no ink may be clipped" reported **27 failures on a
correct build**, and believing it would have sent the next change into the
upscaler: law 70's mistake, on law 70's lever. **The question that decides what
the screen looks like is whether the pixels the window cuts are a repeat of the
last pixels it keeps** — and ask it at 1x as well, because several strips are
cropped on purpose. `tools\uimap\emu\gate_tp_bmp_fit.py` does this, with a
negative control that names the 22 of 31 bitmaps too uniform to be able to fail
rather than counting them green.

### 73. A blit has three numbers — source, crop, destination — and scaling any two of them is a new defect, not a partial fix

`GZWinBMP blttype=normal` slices `imagerect` out of the bitmap and blits that
slice at the window origin. One build scaled the window (285→428) and the bitmap
(285→429) and left `imagerect=(0,0,285,30)` alone, so every row stripe painted
285px of a 428px window and **143px of each row was bare panel**. The builder
skipped those rects because it scales a rect only when the art plan says that
control's art was scaled — and the art plan is computed from the *stock* store, so
art a mod supplies (upscaled through a separate third-party art stage) is
classified "left1x". The mechanism for exactly this already existed: when the
reference does not change but its pixels do, the rect must scale with them. Scope
it to the owning package — a rect may only scale when the scaled bitmap ships in
the same mod-gated dat, or removing that mod leaves a doubled crop over 1x art.
The build printed `rects2x=0` on a file with 24 `imagerect`s and it was read past:
law 54, in one line of the mod's own output.

### 74. When a gate checks a blit, make it read all three numbers — and if it cannot, make it say which one it is not reading

The bitmap-fit gate **passed** the build that shipped the defect above: it read
the window and it read the bitmap and never the crop between them. Two of three is
not "mostly covered"; it is a gate that certifies the exact failure it cannot see.
The first repair then asked the wrong third question — "does the rect still cover
the same fraction of the *bitmap*?" — which flags a glyph whose bitmap was snapped
20→32 while rect and window both went 20→30, i.e. two transparent pixels undrawn
and nothing wrong. **The question that decides pixels is how much of the *window*
gets painted, compared against 1x.** The negative control must be the real
artefact: extracting the script back out of the deployed dat and feeding it to the
fixed gate produced 48 findings in plain language.

### 75. When a cure lands in one path, name every other path that needs it

And a gate may never excuse a finding using a repair that does not run there. The
leaf size-derived rule (law 67) went into `UiSpike::ScaleSubtree`, the runtime
sweep, and never into `build_dialog_static.py`. Statically served dialogs are
**deliberately excluded from that sweep** (`kNeverScale`; running both
double-scales them), so nothing downstream repaired them: a region city bubble's
play button shipped 82px wide over an 83px art cell and the leftover column drew
as a tear. The same control was 83 at runtime and 82 in a static dat — two paths
that must agree, disagreeing silently, and invisibly at 2x and 3x where both rules
coincide. Worse, the gate written for this exact assertion excused the 1.5x
residual with "the parity class is repaired by the leaf size-derived rule": true
in the selective-safe stage, which it scanned, false in the dialog-static stage,
which it had never looked at. It now has a static half that models nothing, reads
the shipped `area=` verbatim, and fails at every tier. **Before a gate downgrades
a finding to a residual, make it assert that the repair it is relying on actually
runs in the path it is looking at.** Scope the cure by measurement: 47 art leaves
moved at 1.5x, the integer no-op is asserted in the builder, and the dialog
dataset stayed at 262 entries with none added, removed or otherwise changed.

### 76. A heuristic that identifies a structure is safe for protecting it and unsafe for rewriting it

`Upscale2x::CellUnit` guesses "this width divides by 3 or 4, so it may be a state
strip". As a guard that only *preserves* divisibility, a wrong guess costs
nothing. Used to *re-time* pixels, it changed **1186 of 2206** sheets and
displaced an advisor frame's flood-filled aperture by a pixel; a seat guard caught
it and the whole attempt was backed out, after which 0 of 941 entries differed.
The shipped version derives the list from the `.UI` scripts that **bind** each
sheet (`tools\upscale\find_cell_strips.py`): **193** sheets, 77 changed at 1.5x,
**0 at 2x and 3x**. **Count what a heuristic fires on before promoting it from a
guard to a transform, and get the real list from whoever actually knows.**

### 77. Assert the measurement with a tolerance, never the model

A guard asserted that a flood-filled aperture *equals* `ScaleRound(offset)`.
Per-cell sampling scales a 55px cell to 83 rather than 82.5, so a source column
legitimately lands one pixel later — the art was right and the equality encoded
the old sampler's rounding. A guard that encodes one sampler's arithmetic fires on
every future sampler change whether or not anything is wrong. Bound it (±1px
here), keep it fatal beyond the bound, and say in the comment which sampler the
bound assumes.

### 78. The defect signature that names a cell-boundary bug

Clean at stock, clean at 2x and 3x, wrong at 1.5x only, and the artefact sits hard
against the **right edge** of a repeated element. That is the next state's art
bleeding into the previous cell because `ScaleDim` snapped the sheet while the
sampler still mapped it globally. Read `int(out/factor)` at the cell boundary and
compare it to `src_cell*count`; the arithmetic answers in one line.

### 79. When two candidate cell counts disagree, the LCM is not a compromise — it is a third answer that is wrong for both

A 180x180 dialog frame is a nine-slice, and the engine's cell is
`img->Width()/3`, so at f=1.5 it wants 270. `CellUnit` returned `LCM{3,4}=12` and
snapped to 276 — purely because 180 happens to divide by 4, which is arithmetic,
not evidence of four states. The cell became 92 where the `.UI` geometry was
scaled for 90, the corner arc stopped short of the window corner, and the straight
edge ran past it as a square block, visible as an interior box overlapping its
frame. This is law 76 applied to *sizing* rather than sampling: fixing the sampler
left the same guess still resizing sheets. Cure: derive the role from the `.UI`
that binds the sheet (`find_nine_slice.py`), and make the derived list
**exclusion-biased**, so an unknown runtime consumer can be missed but never
broken. 6 of 30 sheets moved at 1.5x; 2206 of 2206 byte-identical at 2x and 3x.

### 80. Fix the number that is wrong, not the number that reports it

A first cure made the `imagerect` follow the art — correct as a general guard (law
73) and useless here, because the crop was faithfully reporting an art size that
was itself wrong. Making the report match the bad input moved the defect without
reducing it. Before adjusting a consumer to match a producer, ask which of the two
the design fixes: the `.UI` geometry is scaled by f, so the art must be too, and
everything else follows.

### 81. A diff that compares nothing reports agreement

A 2206-file before/after comparison printed "CHANGED 0" three times because the
two sets used different filename conventions (a normalize-names flag was omitted),
so 0 of 4413 names matched. Only the only-in-one counter exposed it. Every set
comparison must print its **intersection size** next to its verdict, and a
non-zero symmetric difference is a refusal to answer, not a clean bill of health.

### 82. A clipped runtime string has two constants: the surface and the anchor

A placement cost figure was rasterised into a 128x32 buffer **and** right-aligned
at x=124 (= 128 − 4) inside it. Widening the buffer alone made the box bigger and
moved the text nowhere, so it still clipped and the box visibly slid left. That
shift was the evidence naming the second half: **when a size fix moves something
without unclipping it, the remaining fault is an alignment constant measured from
the old size.** Fix both or ship neither; a half-fix reads as "no progress" while
actually being progress you cannot see.

### 83. A `GZWinBMP`'s window size is an output, not an input

GZWinBMP is destination-follows-source: the draw computes
`dst = areaL,areaT + srcW,srcH` and never reads the window rect. A wrong-sized
GZWinBMP window is therefore a *symptom* of a wrong-sized source buffer. Measured:
the game re-sized one such window to 128x32 every time it showed it — caught
parked off-screen carrying a 256x64, reset 80ms later — the sweep fought it four
times, and the scale record tombstoned it as game-managed geometry, correctly; the
fight also flashed on screen. **Before scaling any window, ask whether its size is
computed *from* something; if it is, scale that instead and the window follows for
free.**

### 84. When a 3-byte `imm8` cannot hold the scaled value and the neighbours have no slack, use a cave — never clamp

`83 C3 7C` must become 186, 248 or 372, none of which fit a signed `imm8`, and the
surrounding instructions offered 7 bytes where 10 were needed. The honest move is
a 5-byte `jmp` over the 8 bytes spanning two instructions, into a cave that redoes
both with a full `imm32` and returns. Clamping to 127 would have looked like a fix
at 1.5x and failed at 3x.

### 85. Model callee cleanup or your stack slots are fiction

A frame-slot analysis that treats `call` as leaving `esp` unchanged is wrong from
the first `thiscall`/`stdcall` onward — it put a text origin in a slot nothing
ever wrote, and would have justified patching the wrong instruction. Model it (the
callee pops its args unless an `add esp,N` follows), and sanity-check that every
slot you read was written somewhere.

### 86. The sheet's role decides its sizing rule, and there are three roles

Derived from the `.UI` that **binds** each sheet, never guessed from the number:

| role | needs | evidence | list |
|---|---|---|---|
| N-state strip | `width/N` | window size == one cell | `cell-strips.txt` |
| 9-slice frame | `width/3` | `blttype=edge` / `edgeimage=yes` | `nine-slice.txt` |
| tiled background | nothing | `blttype=tiled` | — |

A tiled sheet is source-follows-destination: the engine repeats the source across
the destination, so its only contract is that the scaled sheet still equals the
scaled **window** — and the window scales by a plain round. Snapping it protects a
divide it does not have and desynchronises the pair. Measured on the god toolbar
rail `{46a006b0,14415876}`: 1x 74x351 equals the window; 2x 148x702 equals the
window; at 1.5x art 528 against window 527, visible as a break in the white line
on the left that is absent at 2x and in stock. Keep every derived list
exclusion-biased, so an unknown consumer can be missed but never broken.

### 87. Rule out your own last change first, by naming consumers — not by feeling

A change had moved 6 sheets **at 1.5x only** hours before a new 1.5x-only defect
appeared: same signature, obvious suspect. The way to clear it is to name every
consumer of every sheet touched (here: four dialog frames, the timer panel, and
Graphs/Data Views — no toolbar), not to argue from plausibility. Do this before
investigating anything else; if it *is* yours, everything downstream is wasted.

### 88. A model that would condemn stock is a broken model, not a finding

A quick check flagged three nine-slice sheets whose 1.5x width was "not divisible
by 3, short by 2". Wrong on both counts: a nine-slice tiles
`[0,cell] [cell,W-cell] [W-cell,W]` and covers any width exactly, and those sheets
are not divisible by 3 at **1x** either — so the model accused the untouched stock
game. **Before believing a defect report from a new instrument, run it against 1x:
anything it condemns there is the instrument's fault.**

### 89. Round half up everywhere, because half-away-from-zero lengthens any span that crosses the origin

`ScaleRound` was `std::llround`, which pushes a negative half value outward
(−16.5 → −17), so a window with a **negative** absolute design origin has both
edges rounded outward and comes out one pixel longer than the same span scaled as
a *length* — the art gets 75, the window gets 76, and the leftover row is a
hairline. It also shifts a negative-origin parent's whole subtree by a pixel
against its own background. Invisible at every integer tier, where `v*f` is exact
and the two rules are the same function, which is exactly why it showed at 1.5x
and never at 2x. Rule: **one rounding convention — `floor(v*f + 0.5)` — shared by
the runtime sweep, the art upscaler and the `.UI` builders.** Two conventions in
one pipeline is a guaranteed off-by-one at fractional tiers, and it will only ever
show up at the tier nobody is looking at.

### 90. The fix is often already in the file, with a comment naming the defect

`RoundHalfUp` sat at the top of `UiSpike.cpp`; its comment already said it
"differs from llround/ScaleRound only at negative half values" and that the art
pipeline convention wins. Five fixes and three probes were spent reasoning from
mechanisms before anyone read it. **Before instrumenting a new theory, search the
project's own source comments for the symptom's vocabulary** — here, "negative"
and "rounding".

### 91. A probe on a lazily-installed hook is a guaranteed null

`BltClassThunk` is patched in only by the disaster-flyout birth path, so two
capture runs with the probe armed logged nothing — and the silence was read as
"nothing draws through this class". Before spending a launch, name what installs
the hook and confirm the planned actions will trigger it. If they will not, the
probe must install it itself. This is one step worse than installed-not-executed:
never installed.

### 92. A "known residual" that exists at one tier only is the defect

A button gate printed `15x {(0,2):347}` / `2x none` / `3x none` for weeks under a
PASS line reading "the known cell-snap, reported not failed" — 347 buttons whose
art cell was 2px taller than its window, at exactly the tier that was being
complained about. Six fixes shipped past it. When a gate reports a non-zero number
it has chosen not to fail on, do not ask whether it is tolerable; ask whether it
**vanishes at the tiers that work**. If it does, stop looking anywhere else.

### 93. Ask whether the artefact is lighter or darker before building anything

Six fixes hunted an *uncovered gap* — abutting rects, art-versus-window sizes,
tiled and nine-slice rules, a rounding convention. Two one-word questions settle
it: lighter or darker, and how long. **Lighter** means something *painted* those
pixels, which refutes the entire gap family in one sentence; a **short segment**
rules out a window edge and a panel-wide tile seam. Both answers cost five seconds
and would have saved every one of those builds. For any visual defect, establish
sign (light = painted, dark = uncovered) and extent before choosing a mechanism.

### 94. The right rule at the wrong scope is still a bug, and hand-lists are how it happens

The cell-divide snap is correct for a state strip's **width** and wrong for its
**height** — a horizontal strip has no vertical divide. That was found, and the
cure was scoped to a hand-written list of four TGI groups; every strip outside
those groups kept the bug. The cure is to key on the **derived** list
(`cell-strips.txt`), never on a hand-list. And check every consumer:
`build_dialog_static.py` was missing the flag as well as
`build_selective_safe.py`, so the first rebuild fixed only half the count.

### 95. An integer-tier control is what stops a self-measuring metric shipping

A new ridge-thickness gate probed a fixed ±2 rows at every factor; once a ridge is
f pixels thick that probe sits inside it and detection collapses, so 2x and 3x
scored as ragged as 1.5x. The metric was measuring its own sampling pattern. The
mandatory "integer factors must read 0.000" control caught it before it became fix
number seven. **Any new fractional-tier metric must be run at 2x and 3x first, and
must read exactly zero there.**

### 96. A cure has as many paths as the geometry has producers — and the third one is the one that ships the bug

The leaf size-derived rule went into `ScaleSubtree`, then into
`build_dialog_static.py`, and never into
`build_selective_safe.py::double_subtree_areas`, the data pre-scale path. Seven
advisor buttons across two HUD scripts shipped an **82px window around an 83px art
cell** at 1.5x only, visible as a break on the right of every icon. Both earlier
fixes were structurally incapable of touching it: one patched `ScaleSubtree`, but
`0x6A15C767` is in `kDataScaledSubtreeIds`, so `ScalePanelRoot` returns before the
child loop and the log had been printing `city panel 0x6A15C767 - 1 windows
scaled` the whole time; and a per-state art sampling change does nothing in the
resting state (output column 82 samples source column 54 under both samplers).
**Before fixing a panel, ask who computes its geometry — the sweep, a static
builder, or a data pre-scale — and check the log line that says how many windows
the sweep actually touched.**

### 97. A gate that models a rule must first prove the rule runs there

A button gate scanned the selective-safe stage and modelled the DLL's leaf rule
for a subtree the DLL provably never walks, then counted the advisors as "parity
class repaired". Its scope filter finished the job: it required the 1x art cell to
equal `r - l` read from the *staged* file, which for a pre-scaled node is the
*scaled* width, so all fourteen fell out at `continue` and were never even
counted. It printed PASS over a visible tear for weeks. Cure: pair staged nodes
with their 1x design by **document order** (ids collide — the two HUD variants
share every id) and judge a pre-scaled node verbatim. Negative control on the old
build: **146 mismatched at 1.5x, 0 at 2x, 0 at 3x.** Then **split the verdict by
cause**, or the gate blames the builder for the upscaler's arithmetic: `cell ==
states * R(cell1x*f)` means the art is right and the window rule is wrong (hard
fail); `cell !=` that means the sheet was snapped (law 70) and it is *reported*,
not failed.

### 98. DBPF file hashes are not reproducible — compare entry payloads

Two builds from byte-identical source differ in exactly **2 bytes, at offsets 25
and 29**: the header timestamp. A file-level SHA-256 therefore reports a false
change on every rebuild, and it nearly aborted a correct fix on a bogus "2x
CHANGED — STOP" reading. The honest integer-tier control is per-entry: parse the
index and hash each entry's bytes by TGI. One such control read **2x 655 entries /
0 differing payloads, 3x 655 / 0**, with 44 changed at 1.5x — all `T-00000000`
`.UI` scripts, no art. Law 40 said equal sizes prove nothing; this is the
converse: unequal hashes do not prove a change either.

### 99. An `.rdata` constant sweep is blind to inline immediates

In one seventeen-launch investigation, every "the constant is inert" verdict was
true and useless: four floats in `.rdata`, a per-zoom pixel table, an effect
instance scale and an effect child scale were all scaled with read-back proof, and
the target never moved. Both real levers were `imm32` fields **inside
instructions** — eight `mov [esp+disp32], imm32` (`C7 84 24 …`, immediate at
instruction+7) for the pin quad, and one `mov eax, imm32` (`B8`, immediate at +1)
for the icon. An immediate scan over the whole file sees them; a sweep restricted
to data sections does not. **State explicitly whether inline immediates were
scanned before calling a constant hunt exhausted**, or it is a filtered null.

### 100. Suppression identifies; scaling does not

Every "make it bigger" probe returned an ambiguous *no change*, which could mean
wrong constant, dead code path, or clamped downstream. The probe that made the
element **vanish** named the drawer in one launch
(`cSC4DispatchVehicleView::Draw` at `0x0046D990`). When you do not yet know who
draws something, ask it to **stop**, never to grow. Growth tests are for after the
owner is known.

### 101. When two elements overlap at similar sizes, 1.5x cannot separate them

Use a factor that needs no interpretation. The offer balloon is two quads — a
64x64 pin and a 35x35 icon. Three consecutive 1.5x launches produced three
contradictory readings of which one had moved, including two wrong calls made off
compressed screenshots. One 3x launch answered correctly and instantly: the pin
tripled, the icon did not. Exaggerate the probe, read the answer, then dial back to
the shipping factor.

### 102. Do not judge a size relationship by eye from a lossy screenshot

The same ±32 quad was called "the icon" and then "the backing" from two zoom
levels of one JPEG, and both calls were wrong. A screenshot proves presence,
colour and gross change reliably; it does not measure ratios. If the answer
depends on relative size, change one element by a large factor and ask which one
moved — or ship a ruler (law 104).

### 103. A constant can be live and still be the wrong constant

`0x00A8819C = 42.0f` applied cleanly, read back correctly, and did nothing
visible, because it feeds the quad's **translation** (`centre = x0 + 42/2`), not
its extent — it had been quietly moving the balloon about 10px the whole time.
"Patch applied, no visible change" therefore does not imply the patch is dead; it
may be alive and aimed at a property nobody was watching. Say which **property** a
constant feeds before concluding anything from its silence.

### 104. Instrument the art to measure, not only to colour

Colouring icons red proves the override wins and measures nothing. Filling each
cell edge to edge with a solid block plus a crosshair turns the **destination
rect** into a number readable off one screenshot — that is what revealed the drawn
size is source-independent. Better still is a **hollow** frame: a 3px border with
a transparent centre, in a colour absent from the game's palette (magenta). It
measures the art's extent *and* leaves whatever draws behind it visible, so one
shot shows both overlapping elements instead of hiding one. An opaque instrument
hides the thing you have not thought of yet.

### 105. The hit box and the art can share one number

The offer-balloon icon's width and height (record `+0xD0`/`+0xD4`, both set from
the single `35.0f` at `0x0046CC47`) are also what the click test consumes, which
is observable in play as only the inner glyph being clickable and not the grey
around it. That is a gift when true — art and tap target cannot drift apart — and
a trap when false. For any in-world element the player clicks, find out which it
is: scaling art without the hit box ships a lie, and scaling the hit box without
the art ships an invisible button.

### 106. A threshold expressed as a fraction of the scale factor collapses at a fractional tier

A gauge draw suppressed its destination stretch when `m < 0.75f * scaleFactor`.
Calibrated at 2x that reads 1.50, an enormous margin over the `m ≈ 1.0` that
already-scaled art produces. At 1.5x the same expression reads 1.125, which sits
*inside* the band of legitimate rounding disagreement between cell-first art (cell
77) and an edge-derived window (87); one gauge landed on 1.1299 and missed the
snap by 0.005. This is law 95 in different clothes: a tier-relative threshold
measures itself. Ask the absolute question instead — here, "is this source still
1x?", which 1x art answers by construction (`R(cell*f) <= win`) while scaled art
overshoots by nearly the whole factor (wanting 116 against a window of 87). Any
guard whose constant is multiplied by the factor is a candidate; check what it
evaluates to at 1.5x before trusting that it works because it works at 2x.

### 107. A frame strip's pitch must divide exactly, and only a fractional tier can break it

The dial draw does `cell = img->Width() / count` with an **integer** divide. A
2805px 55-frame sheet (cell 51) sized total-first becomes `R(2805*1.5) = 4208`,
and `4208/55 = 76` against a true pitch of 76.5 — so the source window slips half
a pixel *per frame* and is 27.5px, a third of a cell, into the neighbouring frame
by frame 54. On screen the dial appears to wrap around. Integer tiers cannot show
it, because `k*W` is divisible by N whenever W is. **A strip defect that appears
at 1.5x and nowhere else is a pitch defect, not a rendering one**, and the cure is
law 86's cell-first sizing, `N * R(cell, f)`. The corollary that kept this one
invisible for weeks: a derivation keyed on `.UI` `image=` references is blind by
construction to code-bound art (these strips come from vehicle exemplar
`0x2BE8E6CB`), so the right rule sat in the codebase at the wrong scope (law 94).
When a divisor is *data* rather than an immediate it cannot be disassembled —
measure it (a needle strip is periodic with period = cell) and gate the
measurement on an independent control.

### 108. A patch that cannot express its value must refuse or widen — never silently truncate

A budget department popup opened for a split second and then resized, at every
tier, for months. The cause was one line — `if (bh > 127) bh = 127;` — clamping a
create height to the `push imm8` ceiling while the width beside it took the full
factor. The window was therefore **born half-patched** (450x127 instead of 450x150
at 1.5x) and something later set the true height: that correction *is* the flash.
The clamp is a constant while the target is not, so the jump **grows with the
tier** — 23px at 1.5x, 73px at 2x, 173px at 3x — which is why no tier-specific
model ever fit, and why "it happens at 2x and 3x as well" was the decisive clue
rather than a complication. Forty lines away in the same file, another patch meets
the identical ceiling and **refuses both of its sites** rather than half-patch,
saying so in the log; that is the correct behaviour, and this site simply did not
follow it. Cure: the cave pattern from law 84 (jump plus NOPs into a stub that
pushes a full-width `imm32` and returns), never a runtime pin — a pin corrects
*after* creation by construction, which is the defect. Corollary, and the
expensive half: **the value was in the mod's own summary line at every launch**
(`bizbox 450x127`), and four instruments were built to go and find it, three of
them aimed at the wrong window entirely. **Search your own log for the number
before building a probe to measure it.**

### 109. A unique anchor proves the text is unique, not that it is in the right container

An id added "to `kNeverScaleIds`" actually landed inside `kAlwaysScaleCityIds`,
where it scaled the very thing it was meant to protect — and the edit looked
correct because the anchor string it was inserted after appeared exactly once in
the file. Uniqueness of an insertion anchor says nothing about which list, array
or function body encloses it. When a fix appears inert, re-read the file around
the edit before theorising about mechanisms.

### 110. A skip list skips the function, not the line

The child walk lives *inside* `ScalePanelRoot`, so excluding an id from that
function removes the entire subtree walk rather than one statement. Before adding
an id to any exclusion list, read what the enclosing function does after the point
where it returns.

### 111. A wrong name in your own source is a search blocker

A constant labelled as one widget in the project's own comments was in fact
another: `0x48E945B4` is the right-drag ring, not the U-Drive-It mission marker.
An audit keyed on the wrong name therefore reported clean while never examining
the widget in question. When an audit comes back clean on a defect that is
visible, verify that the identifier it searched for names the thing on screen.

### 112. A patch that provably ran and changed nothing on screen eliminates its layer

That is a real result, not a failure: it removes an entire layer from the
candidate set. Related, and easy to conflate: a branch tells you where control
*goes*, never who *arrives* — enumerating callers is a separate piece of work from
following a jump.

### 113. A comment can break a gate

Source-layout gates read prose as well as code, so a comment containing the
pattern a gate scans for will fail (or falsely pass) that gate. When a
source-shape assertion trips on a change that only touched comments, the comment
is the finding.

### 114. A repair that reads the state it repairs must be correct on the broken state

Presence is not arming. A repair pass that derives its target from the current
values only works if those values are still meaningful when the defect is present;
if the broken state is exactly the one that corrupts the input, the repair reads
garbage and reports success. Test every self-reading repair against the broken
state, not only against the healthy one.

### 115. A rule consistent for odd stroke widths is inconsistent for even ones at 3/2 — decide per block, never per sheet

At f=1.5 a source run of width w wants 1.5w output pixels, which is an integer
only for even w. Nearest gives source columns multiplicity 2,1,2,1, so a 1px
stroke renders 1px or 2px by the parity of its origin — measured on advisor
sheet 14015571: column runs 1px x106 / 2px x110, where 2x is 2px x216 and 3x is
3px x216, uniform. That is the "ragged / uneven edges" the user named, and it
is arithmetic: a copy rule consistent for odd widths is inconsistent for even
ones and vice versa, which is why the 2026-08 lab's `even_nearest` moved
nothing (26.1% -> 26.2% uneven). The runtime is innocent — every UI pixel is a
textured quad drawn 1:1 at the art's own size, Blt clips and never stretches —
so the fix lives in the art pipeline. A rule that is consistent for both
parities on a straight edge (the edge-claim copy) still cannot help a curve:
every tie on a diagonal or an arc is an isolated staircase step, and on an
anti-aliased button the fallback to nearest produced visible jaggies. The
policy therefore has to be decided **per block**, not per sheet and not per
corpus: a block with a 3-of-4 majority copies; a tie that continues in the
neighbouring block along the edge takes the edge-claim copy; every other block
(a staircase step, a curve, a picture) takes the key-aware 2:1 area average.
Straight chrome stays a crisp copy at one width; curves get the AA a vector UI
renders at 150%. On the 9-slice frame cv1 0.33 -> 0.16; over the shipped
corpus cv1 0.319 -> 0.232 and swc 0.2997 -> 0.2237, with 2x and 3x unchanged
(0 of 2206 sheets, sha1). Both horns of the old trade-off had been rejected on
screen — the area average as "soft" (#200), nearest as "ragged" (#203) — and
neither horn was ever going to win, because the defect was in the parity, not
in the choice between them.

### 116. When no pixel predicate separates two classes the user's eyes separate, the class is a binding fact

After the hybrid reached the screen the user said the thumbnails still did not
look as sharp. A ramp census and a stroke census over 2204 sheets (lab instruments
under `tools\research\sharp15\`, not shipped)
found no threshold that separates them: the glossy mode buttons the hybrid
improved read ramp_frac 0.74-0.99 and stroke density 0.05-0.08; the lot
thumbnails 0.47-0.86 and 0.08. Both are anti-aliased art. What differs is what
the picture **depicts**, and the engine already knows that by how it binds the
art. So `thumbnails.txt` is derived from the binding — every PNG the ItemIcons
+ ItemIconsSub packages carry (485 TGIs, all group 6a386d26) — and those keep
nearest, because a rendered picture wants hard pixels and the 2x/3x block copy
is the user's reference for "sharp". Catmull-Rom and Lanczos were measured for
the soft branch and rejected: at 3/2 neither is sharper than the box on
photoreal art (edge_w 1.66 either way). Launch 2: "Thumbnails are sharp."
Derive a class from what the engine binds the art AS, never from a threshold
on the art — a threshold tuned to separate two populations that overlap will
misfile members of both, and the misfiled ones are the ones the user sees
(#203).

### 117. When both horns of a trade-off have been rejected on screen, put every even outcome in front of the user in-game before shipping any

#200 flipped the 1.5x default from the area average ("soft") to nearest; #203
opened with nearest rejected as "ragged". Once both horns are rejected no
instrument can pick the winner, because the instruments were built to score
the horns. Two things earned the release. First, a whole-image, same-sheet
comparison — `tier_panel.py` lays out the same sheet as 1x / 1.5x shipped /
candidates / 2x / 3x, every pane nearest-magnified to a common 6x-of-1x size so
only quality differs — which is what the user asked for mid-turn ("Not just the
edges. The entire images should be compared") and what chose the candidates.
Second, an in-game A/B without a C# port: `build_variant_tree.py` writes a
preview-tree variant from the Python candidate with the shipped tree's names
and dimensions (law 66), the four preview-tree consumers accept
`SC4UI_UPSCALE_DIR`, and the packages went through Deploy-OnGameClose /
Set-Tier / Test-DatIntegrity like any build. Two launches, two verdicts ("It
all looks a lot better", "Thumbnails are sharp"). Be exact about what the user
saw: launch 2 ran the round-1 tree with the thumbnail sheets returned to
shipped bytes, and the two rule changes that landed after it (the straight-tie
test no longer wrapping at a cell edge; the nearest-key-mask rule replacing 9
hand reverts) were verified by gates — parity 2206 of 2206 sheets byte-equal,
key integrity, the edge-quality report — not by a third launch, with their
scope bounded to the first/last block row or column of a cell and to those 9
keyed sheets. The corollary is the shipping rule: a resampler change the user
has not seen does not ship. The third-party lanes (CamUI, NAM icons, Web
Button, Carbon skin art) were left on nearest at 1.5x deliberately, because
none of them was on the screen the user judged.
