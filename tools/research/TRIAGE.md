# TRIAGE — start here for any new UI defect

**Purpose: cut the time from a reported symptom to a written plan.** Every row
below was paid for with at least one shipped fix. Read this BEFORE
`SC4-UI-ENGINE.md` — this file names which section of it to read, and which
measurement to take first.

The standing failure mode this exists to prevent: re-deriving the same
diagnosis by hand, and filing a fixable defect as unfixable.
**Match the symptom first, then confirm by measurement, then plan.**

---

## 1. THE SYMPTOM TABLE

| symptom on screen | almost always means | lever | precedent |
|---|---|---|---|
| **a panel SPAWNS WRONG then snaps into place** on open, or after the first click | The corrective code exists and is correct — it is simply **not reached before the first paint**. Ask WHICH PASS owns it. Two causes are on record: (a) the dock was reachable only from event-driven callers (`ScaleAllPanels`/`ScalePanelsUnder`/the show hook), never from the tick, so a panel appearing between events painted undocked for SECONDS; (b) the born-correct show path is gated behind `ShowHook`, whose shipping default is `1` = LOG ONLY, so it reports and does not scale | **Prove the branch runs before improving what it does** (law 41/59). Read the mode out of the LIVE ini AND the `installed ... (mode N)` line out of the log — never the default in `Settings.h`. Then: give the consumer its OWN gate (a shared trampoline serves several, and each needs one), add the idempotent call to the tick as belt, and gate the show path on **geometry** (`w/h>0`) because the detour fires BEFORE the visible bit is set | v2.92.0 — two correct fixes shipped first, both on a dead path |
| **a panel is misplaced IDENTICALLY at 2x and 3x** (not a rounding drift — the same wrongness, scaled) | The RELATIONSHIP is wrong, not the tier math. A wrong relationship scaled faithfully is wrong at every tier. The cause on record: an offset **eye-measured off a 2x screenshot** and then generalised, which no amount of tier arithmetic can rescue | **Read the relationship out of the `.UI` design, not off a screen.** If another panel shares the widget id and renders correctly, DIFF THE TWO DESIGNS — that is a free controlled experiment (Graphs and Data Views both carry band `0x0A4A8176`; one is bottom-referenced and right, one was chart-top-referenced and wrong) | v2.89.0 (33px too high at f=3; design gap 48, actual 81) |
| **a sweep or dock SILENTLY DECLINES a window** — no log line, nothing moves, the code looks right | The decline is at a gate that logs nothing. The `SUBGEO` dump sat AFTER the `atNative/atTarget` test, so the one case that needed explaining produced no output at all, and absence read as noise | **Log BEFORE the gate, and give the instrument a positive control.** `SUBCAND` prints every candidate pre-gate (button abs X, the computed targets, both match flags, and the signed ERR to subtract); `SUBSWEEP` proves the block was entered, so silence below it is a MEASUREMENT rather than an absence | v2.86.0 — the sweep had declined EVERY 3x sub-flyout, killing the back-arrow click zone invisibly |
| a constant is commented **"factor-independent"**, or a tier split is documented as **permanent** | Both are claims, and both were false here. `kSubNativeDX = 20` is really `btnW/2 − 27` (20 at f=2, 43 at f=3). The advice-row tier split was blamed on a sign-extended `imm8` ceiling — but an imm8 is an **ENCODING, not a law** | Evaluate the constant at a SECOND tier before believing the comment, and say which tier it was measured at. For an encoding ceiling, **widen the encoding**: rewrite the whole instruction window (`sub imm8` → `lea imm32`), paying for the bytes with folded instructions and stores proven dead BY LIVENESS, with a gate whose positive control drops a LIVE store to prove it can fail | v2.86.0 · v2.88.0 (3x art went 651 → 655, matching 1.5x/2x) |
| a dialog is the **right size and the text reads correctly**, but a coloured strip / background **stops part-way across its row**, leaving bare panel behind it | the **CROP**, not the art. A `blttype=normal` blit has THREE numbers — bitmap, `imagerect`, window — and two of them scaled. Measured: window 285→428, bitmap 285→429, `imagerect` left at 285, so 143px of every row went unpainted | scale the `imagerect` **with** its art. And find out why the builder thought the art had not scaled: the check read `art_plan`, which knows the **stock** store only, so mod-supplied art is permanently classified `left1x` there. Reuse the `RUNTIME_BOUND_2X` rule ("the ref is unchanged but its pixels are scaled"), scoped to the mod-gated package that ships the bitmap | v2.97.1 — and `SC4-UI-ENGINE.md` §3.3 already carried the rule |
| a whole dialog renders at 1× while everything around it is scaled, and **every gate is green** | nothing ever scaled it. Usually a window a MOD **added**: it is in no target list, has no stock twin to diff, and is never built, so no verifier can see it | compare the live rect to the `.UI`'s own 1× `area=` — equal to the pixel means no lever ran (step 0 below). Then resolve the owner per TGI with `tools\dbpf\who_owns_tgi.py`: the last line it prints is the winner, and it must be the mod's package | v2.97.0, CAM's Village Hall info screen |
| "drawn **twice**" / a repeated pattern inside a box that is itself the right size | a **src-follows-dst** class: it computes its SOURCE rect from the WINDOW, so under-sized art **tiles** instead of shrinking | ship the art at the **window's** size | `cSC4WinAuraBar` |
| "**duplicated** icon", two half-size states side by side in one cell | a **multi-state strip** at 1x inside a doubled cell | ship 2x art (check `.SC4Lot`/`.SC4Desc`, not just `.dat`) | Grutzehaus lot icons, picker dialogs |
| "it **jumps**" / wrong for a split second then snaps into place | a **reactive pin**: the game re-lays on some event, the sweep corrects a tick later | make it **born correct** — ENGINE §4.7 rows 3/4 | Data Views, flyouts |
| a window that owns a **render SURFACE** (minimap, data-view map) flashes stale content on open, or a "fix" to it CRASHES | the window scaled but its surface did not: these surfaces are **one-shot Init at vtable+`0x0C`** — calling Init on a live surface corrupts it | destroy + **recreate** at the new `blitSize` (`[+0xE4]`), copying the game's own pattern; latch on the **POINTER** so a new city load re-fires | v2.21.1 crash → v2.21.2 cure |
| you want to fix something "at city open" | **walking the tree inside `PostCityInit` HANGS the game** — measured, not feared | find a later, always-running arm point; never widen `PostCityInit` | the law is in `src\UiSpike.cpp`'s file-header rules (grep `PostCityInit message HANGS`); the later arm point it names is `UiSpike::ArmDeferred`, and `UiSpike::EarlyDockTick` (grep `THE THREE LEVERS AND WHY THIS IS THE ONE LEFT`) records what each alternative cost |
| the WHOLE city HUD is wrong for about a second after a city opens, not one frame | the first pass runs **0.8–2.3s after arm** — the tick is **starved during the load tail**. There is no delay constant to tune; the pass is blocked, not late | needs a lever that runs before the first paint; **check when the candidate mechanism INSTALLS** — the `DFG` Plot patches install inside that same late pass | city-open flash |
| a show/visibility hook sees nothing, so the conclusion is that the window "isn't shown" | **NULL TRAP.** `SetFlagDetour` fires only on a **0→1 transition** (`(bits & 1) == 0`). A window **created already visible** never transitions and is invisible to it | prove the hook CAN see the thing (positive control) before believing its silence | refutes `ShowHook=2` for born-visible windows |
| a panel must be correct BEFORE its first paint, and the sweep is too late | **THE PROVEN LEVER (v2.41.19): scale it from inside the `cGZWin::SetFlag` detour** — the game's own stack, which keeps firing AFTER city init returns — gated on the subtree's **design child count** (the direct "fully built" signal; a consecutive-checks stability test costs ~625ms because SetFlag barely fires during load). If the subtree owns a one-shot surface, the scale and the recreate are **ONE action** (`TryRecreateMinimapSurface`) — splitting them is the v2.41.15 crash | fired at +328ms / +109ms against the sweep's +968ms; the sweep then skips it via scaleMap | EARLYDOCK |
| you want to scale something INSIDE `PostCityInit` and reason "the ban is about the 456-window full walk, mine is only a small subtree" | **MEASURED: ~25 windows of `SetW`/`SetH` there CRASHES the city open.** The threshold is **not window count** — two byte writes (`[+0xFD]`/`[+0xFE]` + `InvalidateSelf`) are safe at the same site, proven over several runs. **Mutating window GEOMETRY during city init is categorically different from writing flags, at any size** — the game's own init continues after you and re-lays against geometry it did not expect | flags/invalidate at `PostCityInit` = OK. Geometry = NO. Find a lever on the game's own stack AFTER the tree is built | v2.41.15 crash, `EarlyBake` |
| you want the pass to run sooner than the 1-2s post-arm gap, by ANY message-queue means | **THE WHOLE FAMILY IS DEAD, MEASURED.** A posted `WM_APP` beat `WM_TIMER` by **15ms** (one timer period): the game does not pump messages **at all** during the city load tail, so there is no queue to jump. `WM_TIMER` cadence, `ShowHook` and `WM_APP` all die on this one fact | the lever must be something the GAME itself calls during load, or data | v2.41.0, city-open corrupted minimap |
| you are about to add an id to `kDataScaledSubtreeIds` to make a panel born-correct | that list grants **TWO** powers — "do not scale this" **and** "do not walk here" (`ScalePanelRoot` RETURNS EARLY). If anything else runs inside that child recursion, you kill it too | check BOTH meanings. The HUD dock's god/mayor **flyout docking** runs inside its recursion — adding `0x0987B48F` unstuck every flyout | v2.41.1 |
| data-pre-scaling SOME children of a container moves or mis-anchors the WHOLE container | the container's rect is the **UNION OF ITS CHILDREN WITH NO CLAMP**, so one pre-doubled child that overhangs the design frame grows the union and drags an edge-anchored parent | **all children or none** — and if "all" is barred (for example because the walk carries other work), the container is runtime-scaled ONLY | v2.41.2, `CITY-DOCK-OVERLAP.md` |
| you need a window's pixel buffer and reach for `[win+0x6c]` or a `GetBufferToDrawTo` vtable slot | `[+0x6c]` is the **DRAW CONTEXT**, not a buffer. The slot list is FIXED in the code: 93 `GetDrawContext` = `[+0x6c]`, **94** `GetBufferToDrawTo` = `[+0x68]`, 101 `GetPrivateBuffer` = `[+0x64]`; any table that omits **89 `Draw`** is off by one. Slots 95–97 are hooked and unnamed, and 87..97 is not a zero-arg group — the community names for 94–97 include slots that take arguments | use MEASURED per-class offsets (minimap: `[+0xE4]` blitSize, `[+0xF0]` surface ptr, `[+0x114]` embedded render buffer). Never call a slot by guess: wrong arity = stack corruption. Canonical table: `SC4-UI-ENGINE.md` §2.1 | v2.41.4/.5; the corrected slot table in `src\UiSpike.cpp` (grep `THE SLOT TABLE BELOW WAS OFF BY ONE`) |
| a blit census reports "every draw corrected" but the screen disagrees | **THE WINDOW OWNS A PRIVATE BUFFER AND THE HOOK IS ON THE WRONG CHANNEL.** There are **three** ways out of a buffer — slot 29 `Blt`, **slot 20 (`+0x50`) the private-buffer present** (`0x0099BA3E`), and `PlotPresent` `0x0099C498`. A slot-29 hook is blind to the other two by construction. There are also **two** buffer classes: `0x00AC1400` and `0x00ADB418` | check `GetPrivateBuffer` (slot 101) first; watch slot 20 on **both** classes; arm a counter that counts ALL calls for ANY window (`gS20Any`) so a null can be graded | PRESENTWATCH, ENGINE §2.3 |
| art shows white seams / state bleed / a 1px desync, **at 1.5x only** | the sheet was sized by the **wrong ROLE**. Strip → `width/N`, 9-slice → `/3` and 3 alone, tiled **or 1:1 window-bound** → **no snap at all**. `LCM{3,4}` is a third answer that is wrong for both | find the sheet in the **derived** list (`find_cell_strips.py` / `find_nine_slice.py` / `find_no_snap.py`), never hand-classify. Integer tiers are a structural no-op, so 2x/3x is the control. The shipped no-snap list is `no-snap.txt` (121 sheets, generated by `find_no_snap.py`), and it is what `Rebuild-Corpus.ps1` feeds `--no-snap`, as do `build_selective_safe.py` and `build_dialog_static.py`. The 10 `blttype=tiled` sheets are a strict SUBSET of those 121, and `Upscale2x.cs` has no `--tiled` flag at all. The role is wider than `blttype=tiled`: `find_no_snap.py` also admits any sheet a `.UI` binds 1:1 to a window of exactly its 1x size, which is 111 of the 121 — and it measures 98 such art/window pairs flush at 1x and 2x and diverging only at 1.5x by 1-6px, which is this row's own symptom | `no-snap.txt`, ENGINE §4.6c |
| a widget is 1x inside a correctly-doubled window, and its art is supplied at runtime | **code-bound art** the reference-driven pass never saw | `CODE_BOUND_TGIS`, or the GZWinBMP draw hook (BMPX) | mission markers, My Sims faces |
| a whole dialog opens **crushed / corrupted** | it is a **static** dialog the sweep does not scale | `DialogStatic` TARGETS (doubles `area=` in the script) | budget family |
| a panel is right but **one child** stays 1x | that child is **code-created** (live children > scripted `area=`) | patch the builder's constants | ENGINE §4.7 row 3 |
| text **clipped** or not wrapping, with a sensible break AND a mid-word cut | `GZWinText` regime 3 (break on `\n` only, then CLIP) | `SetWinTextFlag(0x0002)` + resize | law 24, ENGINE §5.0 |
| text **wraps to more lines than stock** in a box already scaled by `f`, and the overflow shows at the BOTTOM | **THE BOX IS AN INPUT, NOT AN OUTPUT** (law 48). SC4's wrap call `sub_896957` (font `vt+0xB8`, multiline=1/wrap=1) **READS** `r->left`/`r->right` at `0x00896979` and never writes them; the only output is `bottom = top + nLines*lineHeight`. And ink does **not** scale linearly with point size — measured **x2.13** per doubling (n=17), not x2.00 — so `round(stockBox * f)` is about 6% too narrow and wraps MORE than stock | size the box from the **FONT**, not from `f` (`tools\uimap\emu\emu_text_extent.py` gives the widths). A defect whose *symptom* is vertical can have its *cause* on the horizontal axis | v2.55.0, ENGINE §5.4.5/§5.4.7, law 48 |
| **four separate fixes each MOVED the collision without curing it** — every patch is measurably applied, the log confirms the new rects, and the elements just collide somewhere else | **THE PATCHES ARE ON OUTPUTS INSIDE A BUDGET NOBODY HAS READ** (law 49). The number that decides the layout is a constant in the **BUILDER**, and no instrument aimed at the symptom prints it — every probe printed the resulting RECTS. This is the second instance of the shared-width-budget family and the more expensive one, because here the *chart* did not lay out its own legend at all: the **PANEL builder** `sub_76D3D0` did, once per build, from six hard-coded literals plus the window width | **stop probing the output; disassemble the BUILDER.** Find the allocation site for the child (whole-`.text` scan for the entry allocator: this case had exactly ONE call site each, `0x0076E20A` / `0x0076E220`) — whoever allocates it is whoever lays it out. Then re-derive the whole budget at `f` and patch it at birth. **Probe the output twice; after that, read the code that computes it** | v2.55.0 — six patches shipped before the builder was read (v2.50.0, v2.51.0, v2.52.0, v2.54.2/.3/.4): four rewrote an output rect, two were field-level writes. ENGINE §5.4 |
| element **overlaps** its neighbour only when the text is long | a 1x inset/column constant against a 2x font | byte-patch the inset (watch the imm8 ceiling) | ordinance/budget insets |
| shipping 2x art for one element makes a **different, neighbouring** element vanish | a **shared width budget**: the two live in one row/strip whose total is a hard constant, so growing one evicts the other. Reverting the VANISHED element's own art will NOT bring it back — that is the diagnostic, not a refutation | find the constant that sums the parts and re-derive it from the art (`round(stock*f)` per part + the unscaled reserve); the two halves ship and revert TOGETHER. **The budget need not be one constant** — the Graphs legend's was **SIX** (`110 / 108 / 90 / 106 / 10x6 / 4 / 4`), all measured off `winW` inside one builder, and it stayed invisible through four fixes because no instrument printed any of them | advice row `83 EE 3D` @`0x0079388F`; **Graphs legend, `sub_76D3D0`, v2.55.0 — the second instance of this family, and the one that proves the constant can live in a builder nobody has censused**; ENGINE §5.1, §5.4 |
| "it's off the edge" / clipped at a boundary the pane's own width says it should clear | the arithmetic is measuring against **`GetW()`**; the real boundary is the **content width** `GetW() - 2*gutter - scrollbarW`, and `scrollbarW` is read LIVE so it moves per tier | measure the content width, not the window; state which one the arithmetic used | law 25, ENGINE §5.0 |
| correct on later uses, wrong on the **first** use of a session | an **uninitialised latch**, not a race — later uses are PRE-WARMED, not faster | prime the latch at birth **or check whether the latch is one this mod created** (law 14: a first-open jump is as likely to be this mod's own corrective move; one such cure was DELETING a centring, because SC4 had placed the dialog correctly all along) | v2.36.2, quit-confirm dialog |
| an element is absent on FIRST open but appears after an interaction (scroll/click) | EITHER **unpainted** (a hook landed after the first paint) — OR, if it **survives a forced repaint, it is a stale DECISION, not a stale frame**: the draw READS a flag/state some earlier code computed, and the interaction is what RECOMPUTES it. v2.39.4 shipped the repaint cure on this symptom and it cured nothing — the arrow flags `[0x118]`/`[0x119]` were computed at open from MIXED units (2x window, 1x item pitch = "nothing to scroll") | first try ONE forced `InvalidateSelfAndParents()` (one-shot per window, never suppression); **if that fails, stop repainting — find what the draw computes FROM and make those inputs consistent at BIRTH** (v2.39.5: born item metrics) | law 18 + v2.39.5 |
| a family still flashes or jumps though the fix for that symptom shipped | it is on an **older MECHANISM GENERATION** — the fix was applied to its siblings and never back-ported | `tools\research\MECHANISM-GENERATIONS.md` names the generation per family and the one measurement that confirms it | Create Disaster was gen 1 for 28 versions |
| works in city 1, broken in city 2 | a function-local static holding a **dead pointer** | clear it in `Disarm` | law: second-city lifecycle |
| two of the mod's own lists contradict each other about one id | check what each list's predicate is actually **consulted by** before calling it a defect. `kNeverScaleIds` is honoured only by `ScaleOnShow` (dormant at the shipped `ShowHook=1` default) and the city sweep's DIRECT-children loop — NOT `ScaleSubtree` — so it means "never scaled **by the sweep**" and does not protect against recursive descent. An id can sit in it *and* in `kCityDialogIds` (a different mechanism, for transients the sweep cannot reach) with no contradiction | measure first (`who_owns_tgi.py` plus the staged corpora): if the id is data-born at every tier, the second entry is **belt-and-braces for a package-load failure** — deleting it removes a safety net. Document and assert the overlap instead | law 24 |
| a dialog/panel opens at **stock** size although the data override is deployed and correct | **another plugin owns that TGI** — root `Plugins` files load BEFORE subfolders, so a root package can never beat one in `150-mods\` | rebuild from the **MOD's** copy into `zzz-SC4UIScale\`, gated on that mod's presence | Building Styles, quit confirms |
| a flyout docks against the WRONG button (one row off, or wildly off) after a mod is installed | the mod **replaced that flyout's script and MOVED its hidden `0x0000AAAA` marker**, while the dock table caches `R = -marker(1x)` measured off the STOCK script. Measured: LANDSCAPE marker (3,27)->(3,59); SIGNS & LABELS (3,183)->(4,5) = 178px of misdock | dock from the **LIVE** marker: `target = spawnButtonAbs - markerOffset(live)` (the marker is scaled with the subtree, so its live L/T are screen units); keep the constant as the fallback for markerless scripts. **Check BOTH dock paths** — an id that shares a window with a god flyout is `mayorOnly=false` and docks on the GOD path's mayor branch, NOT the mayorOnly loop, which is exactly why Signs & Labels came good and Landscape did not. Acceptance is arithmetic: `flyoutPos + markerOffset == buttonAbs` to the pixel | v2.43.1/.2 |
| a runtime-supplied image is 1x **intermittently** — right on one open, small on the next, and clicking the item fixes that one | **AN INSTALLED HOOK IS NOT AN EXECUTED HOOK.** A draw override can be installed on every instance and still never run: the engine paints some opens through a path that does not call the per-window Draw, so the cell shows whatever its private buffer holds (`winflag_pbuff=yes`). MEASURED: new dialog object, **25 instances hooked**, 13 s on screen, **zero** draws through the hook | count **CALLS per visible event**, never installs — a per-open census of counts cannot saturate, unlike a line budget. Then kick ONE `InvalidateSelfAndParents()` through **each hooked LEAF** (the ROOT alone does not reach them — measured). If a census still reads 0 with the leaves kicked, STOP: no repeat sweeps (ghost-heal is dead), disassemble the blit path | v2.42.3/.4 |
| a control renders as a **plain filled bar** — no glyph, no caption, just `fillcolor` — at 2x only, while identical siblings render fine. It may ALSO silence text on OTHER windows of the same panel | a **dangling art reference**: the `image=` TGI resolves to NOTHING (classic cause: a **STALE DEPLOYED DAT** carrying clone refs from an older classification epoch — the clones stopped shipping when the strips went `EXCLUSIVE/2x-in-place`). The working/broken split correlates EXACTLY with which strip each sibling references, and the neighbouring bands are intact: they come good when the buttons' refs are fixed | diff the DEPLOYED script against the FRESH build output (extract both; the diff is the diagnosis), then check `refmap.csv` for the TGI's current classification. Stale and fresh dats have IDENTICAL sizes and entry counts — only content hashes catch it; the `Test-DatIntegrity` DEPLOYED==BUILT section is the standing guard | radio rows and bands |
| **bright / white SEAMS across art**, or icon states bleeding into each other — **at 1.5x only**, 2x and 3x clean | the game **cell-divides sheets with an INTEGER DIVIDE baked into its own code** (`cell = img->Width()/3` for nine-slice — the `.UI`-bound drawers are `GZWinBMP 0x009BC325` (EDGE branch) and `GZWinBtn 0x009B05E0`; each divides its own source rect and then calls the blitter `0x008D8800`, which contains no divide; `0x00794100` is `cSC4WinAlertBorder`'s own draw and appears in no `.UI`. See `SC4-UI-ENGINE.md` §4.6c; `width/4` for four-state strips). If the scaled dimension stops being divisible by that count, `cell*count` no longer covers the sheet and every cell drifts, drawing a sliver of the NEXT state — which is the bright hover art. **An integer factor preserves divisibility automatically, so this is STRUCTURALLY IMPOSSIBLE at 2x/3x** — measured 31% (/3) and 43% (/4) broken at 1.5x, 0% at both integer tiers | snap the fractional factor's output to preserve the SOURCE's divisibility (`Upscale2x.cs::ScaleDim` + `CellUnit`) — **but THE SHEET'S ROLE DECIDES WHICH DIVIDE, and one role has none (law 86; the `wrong ROLE` row above is the live entry). `ScaleDim` is the lever, but it snaps to whatever `CellUnit` hands it, and `CellUnit` answers per ROLE (`tools\upscale\Upscale2x.cs::CellUnit` — mind the stale copy under `_working-backup\`): N-state strip → the LCM of whichever of `{3,4}` divide the SOURCE dim (the `kCellCounts` array `CellUnit` walks); 9-slice frame → `{3}` ALONE (`kNineSliceCounts`, selected by the per-file `sNineSliceOnly`), because a 180px frame divides by 4 as well and `LCM 12 → 276` satisfies NEITHER count against a `.UI` scaled for 270 (the worked 180px case is in the comment above `sNineSliceOnly`); tiled **or 1:1-window-bound** → **NO SNAP AT ALL** — `CellUnit` returns 1 on `sNoSnapThis` — because those sheets have no divide to preserve and their only contract is with the WINDOW, which scales by a plain round, so a snap can only desynchronise the pair (the god-toolbar-rail table in the `sNoSnapThis` comment measures it). Height is a fourth answer, not the same one: a strip is cut horizontally only, so its height is taken EXACT (`--no-height-snap` sets `sNoHeightSnap`, `--height-exact-strips` fills `sHeightExactStrips`). Read the role out of the DERIVED lists — `find_cell_strips.py` / `find_nine_slice.py` / `find_no_snap.py`, that last one carrying the tiled members too — never hand-classify from the number.** Do NOT reach for the resampler: **nearest-neighbour only copies source pixels, so it cannot introduce a colour the 1x art lacks** — a white line absent from the source can never be an NN artifact, which rules the upscaler out in one sentence | `rebuild_namicons.py`'s `non-div4` counter |
| an element renders **PINK / MAGENTA**, or gains pink fringes/outlines | magenta `0xFF00FF` is the game's **TRANSPARENCY KEY**. Any interpolating filter (bicubic, bilinear, "HQ") moves an exact key pixel to `0xFE01FE`; the key test misses it and **the key colour draws**. Every pixel bordering a keyed region fringes | never interpolate this game's art — nearest-neighbour at EVERY factor. Free instant detector: **a package whose size moves the wrong way** (1.5x has 2.25x the source pixels against 2x's 4x, so a 1.5x dat must be SMALLER than the 2x one; bicubic doubled it) | `README.md` rejects interpolating scalers |
| a status/report script says **none of the mod's packages are active** while the game is plainly using them | a **duplicated slot silently overwriting the answer**. `Deploy-OnGameClose` writes `X-<tag>.dat` AND refreshes the `X-<tag>.dat.x1-disabled` twin, so both exist; a plain hashtable assignment keyed on the tier let `.dat.x1-disabled` (which sorts later) overwrite the active entry, flipping every family to `active=false` | make the ACTIVE file win the slot and REPORT the duplicate. **A status instrument wrong in the safe-looking direction is worse than none** — "nothing of the mod is live" invites exactly the wrong next move | `Set-Tier.ps1` |
| a panel is placed correctly by the game's own math and the thing ATTACHED to it (stem, arrow, connector, pointer) ends up somewhere else — or the attachment is fixed and the panel then overflows the screen | the two are a **COUPLED PAIR welded by a LATCH**: the attachment is a blit at an origin stored per-open inside the container, so relocating the container slides it 1:1. Fixing either half alone is not partial progress, it IS the bug (v2.45.0 shipped half and was withdrawn the same day) | ship BOTH halves in one action: container → the game's own clamped expression at `f`; sprite → offset by **minus** that move, pinning it to its **measured-correct current** value (do NOT re-derive it — the game's own convention may legitimately differ, here by 26px on X). Prove the mechanism first for free: override that single field in an offline model of the draw — if the sprite moves and the neighbouring rects stay byte-identical, that field is the sole input. Move the **hit box** with the sprite, and make the new gate able to FAIL on the old code | v2.46.0, laws 42+43 |
| an icon/strip is **still wrong after a mod is installed** although the coverage census says that TGI IS covered, and every sibling in the same flyout came good | **THE COVERAGE PREDICATE IS NOT THE LOADER'S.** "Is this TGI in one of the mod's packages" and "does the MOD's file load LAST for this TGI" are different questions, and they disagreed for exactly **1 icon in 392** — the one the player could see. `0x2A3ED76A` (Rail) is a STOCK icon this mod had always doubled in the ROOT package; NAM ships it from a SUBFOLDER, root files load before subfolders, so NAM won forever. A folder-level check (`'zzz-SC4UIScale' > '770-network-addon-mod'`) is NOT this check — it was green the whole time | re-derive the winner **per TGI** across BOTH plugin trees and assert it is the mod's; ship the loser from `zzz-`. `gate_namicons.py` §3b is the reference implementation, verified RED on the old package before it went green. Walk with the `\\?\` long-path prefix — NAM nests dats to 298 chars and a bare `except OSError` reads as "no icons here" | v2.93.0 |
| a census / scan / `find_tgi.py` says a TGI or file **does not exist**, and the next move is to relax a guard or call the reference dangling | **CHECK THE INSTRUMENT'S OWN INVENTORY FIRST.** `find_tgi.py` carried a HARD-CODED list of seven archive names and a docstring calling it "all seven"; the install ships **nine**. The splash background lives in `Intro.dat`, which was never opened — so a build guard was relaxed and the shipped splash used CAM's background (99.72% of pixels differ from stock). The tool even warned that its negatives are not "dangling", and the warning pointed at the wrong axis: it said *Plugins* were unscanned, and nobody asked whether the GAME side was complete | **derive the inventory, never list it** — enumerate the directory so a tenth archive is covered for free. And state the positive control: prove the scan CAN see a known-present item before believing a null (NULL IS NOT EVIDENCE) | v2.93.0 |
| a **stock / control capture** still behaves like the modded build | **SC4's plugin scan is RECURSIVE.** A stash folder INSIDE `Plugins\` disables NOTHING: 132 dats (98 MB) + 30 DLLs loaded through every "stock" capture while the top-level listing looked clean. Only an extension rename or a move OUT of the tree disables anything. It compounds with the THIRD `FontStyle.ini` (`<install>\Apps`) — a capture is clean only when both are | park stashes as a **SIBLING** of `Plugins\`, never a child. To verify a stock claim, enumerate BOTH plugin trees **recursively** and count files — a directory listing is not a census. Any capture taken with a stash inside the tree is contaminated | recursive plugin scan |
| the **first city open of a session** takes about a minute with a big plugin load-out, later opens are fast | MEASURED, not folklore, and there is **no lever**: 54.3 s wall / 53.1 s CPU / 934 MB in **1,902,959 reads** (~515 B each) against 9.2 s / 3.3 MB / 4,008 reads for city 2. `CPU/wall = 0.92` = a saturated core (the game is pinned to one), and a 15-s stretch did ZERO disk. It is a one-time lazy load of the plugin corpus, **CPU-saturated, not disk-blocked** | do not offer a prefetch cure — prefetching only helps disk WAIT and there is none. No ini key, no hook, and nothing the DLL can call triggers it earlier. The only real lever is repacking the mod into fewer, larger, uncompressed archives, and the **user-vs-kernel CPU split** is what decides syscalls against parsing | v2.93.0 |
| a per-thread / per-process counter reads **~0** for an elevated target, or an affinity mask reads `0x0`, and the summary prints a confident verdict anyway | **A BROKEN INSTRUMENT THAT CANNOT DECLINE TO SPEAK WILL FABRICATE.** A thread census printed "ONE thread does essentially all the work — unpinning CANNOT help" from **20 ms across 20 threads** while the process had burned 186,000 ms. `Win32_Thread` (and `System.Diagnostics`) return zeros when the querying shell is not elevated and the target is — SC4 runs under a RUNASADMIN shim | make every summary **RECONCILE against an independent total first** and refuse to render a verdict below a stated threshold, naming the likely cause. Print the ratio BEFORE the ranking | elevated-target thread census |
| the change is INSURANCE for a window/state nobody has ever observed, so there is nothing to eyeball and "no change" proves nothing | inert and BROKEN look identical from the outside. A data half whose runtime half never fires leaves a 2x child inside a 1x root — strictly worse than untouched, because the city sweep skips `vis=0` and only `kAlwaysScaleCityIds` grants the exception | make the probe **ADJUDICATE, not sight** (law 44): print the verdict — `926x264 born/scaled 2x (insured)` against `463x132 still 1x - insurance did NOT take` — plus the facts that decide the next move (parent id, sibling-vs-child, visibility) so ONE appearance closes the question. Let it test the PREMISE as well: the question "which vehicle spawns it" had the measured answer "none — it is resident and hidden", which no amount of vehicle-cycling could ever have produced | v2.48.0/.1, law 44 |

**If the symptom matches a row but the current diagnosis says "unreachable",
suspect the DIAGNOSIS** (law 34). That exact combination has been wrong twice.

---

## 2. THE FIRST MEASUREMENTS, IN ORDER (all cheap)

**STEP 0 — DOES ANY LEVER TOUCH IT AT ALL?** Before diagnosing HOW a window scales
wrong, ask whether **anything ever scaled it**. The log answers in one line: if
the live rect equals the `.UI`'s own 1x `area=` **to the pixel**, no lever ever
ran — it is not a rounding bug, a hook that missed, or an art mismatch, and
every theory in the tables above is off-target.

```
MWKID  0  id=0x10000005  (150,38 600x525)      <- CAM's info screen, live
.UI     area=(150,38,750,563) = 600x525        <- its own 1x design
```

A dialog a MOD ADDED is the usual cause: it is in no TARGETS list, has no stock
twin, and is never built, so every builder gate stays green while it renders at
1x under scaled fonts. `tools\dbpf\who_owns_tgi.py` lists every archive on disk
that carries the TGI, in load order; the last line it prints is the winner.

1. **Read the element's own section** in `SC4-UI-ENGINE.md` /
   `DYNAMIC-CONTROLS.md` / `BUDGET-DETAIL-ANATOMY.md` and the **FAILED-ATTEMPTS**
   list. The answer is often already written down. Quote it in the plan.
2. **Find it in the `.UI` corpus.** `grep` the 330 extracted scripts for the id
   or a bar-shaped `area=`. If it is scripted you know its stock rect for free —
   and whether it is a standard class or an `IGZWinCustom`.
3. **Diff stock against staged — then ask WHO ELSE SHIPS THAT TGI.** Compare the
   extracted stock script with the copy the builders stage. This tells you in
   one step whether the WINDOW is already doubled — and therefore whether the
   bug is geometry or content. **If the live rect matches NEITHER stock NOR the
   staged copy, stop and scan every dat on disk for that TGI** (game archives +
   every plugin subfolder, via `tools\dbpf\find_tgi.py` and
   `tools\dbpf\who_owns_tgi.py`). A third-party owner is invisible to a two-way
   stock-against-staged diff, and that blind spot cost five days on the quit-confirm
   dialog — the winner differed from stock by one pixel.
4. **Read the live log**, never a screenshot: `MWKID`/`VWKID`/`RGKID`/`DPROBE`
   print id, vtable and rect the moment anything appears. Compare live size to
   staged size.
5. **Only now the disassembler.** Whole-image scan for the window id or the art
   instance — a count of 1 proves a single code path and kills law 16 outright.

Every MEASURED value in this project has landed first try; every inferred one
has cost 2-3 builds.

---

## 3. BEFORE YOU BELIEVE A NULL

- **State the positive control.** What would this instrument have printed if
  the thing existed, and has it *ever* printed that?
- **Two nulls that agree are still one null** unless the instruments have
  independent failure modes (law 34).
- **Known blind spots, measured:** `RGKID` stops above deeply-nested children
  (law 20 — it skipped the region rating bar twice); the UI buffer class never
  composites to the screen, so a blit hook on it cannot see full-screen art.
- An A/B only means something if the toggle is in the **same subsystem** as the
  defect. Check that before reading its result.

---

## 4. THE LEVERS, AND WHAT EACH CAN REACH

| lever | reaches | cannot reach | cost |
|---|---|---|---|
| **art data** (`SelectiveArt` / `DialogStatic`, `CODE_BOUND_TGIS` for art with no `.UI` ref) | anything whose pixels come from a dat | geometry, code-drawn content | rebuild + entry-count update |
| **`.UI` static doubling** (`DialogStatic` TARGETS) | dialogs the sweep does NOT scale | anything the sweep also scales (double-scales) | rebuild |
| **runtime sweep** (`UiSpike`) | **any window the walk actually REACHES**, idempotent via `scaleMap` (keyed on POINTER) | content painted inside a buffer; anything re-laid after the sweep; **any DESCENDANT of a `kDataScaledSubtreeIds` root (that array in `src\UiSpike.cpp` — advisor strip, the three Graphs roots, both U-Drive-It console roots AND the four BUDGET roots, ten ids in all): `ScalePanelRoot` sizes and anchors the ROOT, then RETURNS before the child-enumeration block. That is the "do not walk here" power the `kDataScaledSubtreeIds` row above already names. Their descendants are sized in DATA by `build_selective_safe.py::double_subtree_areas` — the sweep owns the root's size and anchor, and nothing below it. The gate is in `ScalePanelRoot` ONLY (`IsDataScaledSubtreeId` has exactly one call site), so any path that enters such a subtree via `ScaleSubtree` instead would double-scale it.** | none |
| **byte patch** (`CodePatches`) | literal immediates in a builder | runtime-composed values; >127 in an imm8/disp8 | build; verify bytes first |
| **draw hook** (GZWinBMP vtable `0x00ADF6A0`, slot 88) | runtime-supplied images drawing 1x | anything not drawn by that class | build |
| **detour on a placement call** (ENGINE §4.7 row 4) | code-created windows whose constants are coupled | — | build; needs `scaleMap` drain |

**Slot 88 (`vt+0x160`) is the PER-CLASS "draw myself"**, not the composite
driver: `cSC4WinAuraBar 0x797CC0`, `GZWinBMP 0x9BC325`, `GZWinBtn 0x9B167D`,
all distinct. The vendor header `cIGZWin.h` is **missing one virtual** (a
delta-move at real slot 57, `0x0099BD27`: `mov edx,[ecx+0xB4]; add edx,[esp+8]`),
so every header-derived slot NAME above 56 is one too low. The hooks are
installed by INDEX, which is why they land correctly; only the header's names
are shifted.

**Three blit behaviours exist** (do not assume the first):
1. **dst follows src** — GZWinBMP plain path: 2x art ⇒ 2x draw.
2. **stretch** — the 9-slice EDGE path.
3. **src follows dst** — `cSC4WinAuraBar`: under-sized art **tiles**. Compare
   art size against the **window**, not against the source rect.

---

## 5. DEAD ENDS — never retry without new evidence

- **Suppressing or deferring paints** (`FlashGuard`). Measured: it did not fix
  the flash. Permanently rejected.
- **A `SetFlag` show hook** for on-demand windows — they are BORN visible, so
  there is no false→true transition to catch.
- **Data pre-scale of a composed HUD root** — it broke mayor mode outright
  (v2.33.0, withdrawn). Row 2 requires *fully scripted and not runtime-composed*.
- **Changing the sweep cadence to win a race** — it already runs every ~16 ms
  and `WM_TIMER` is lowest-priority. Remove the race instead.
- **Measuring text through `cIGZFontSys`** — overloaded vtable groups are
  reversed by MSVC; you hit the wrong slot.

---

## 6. BEFORE WRITING THE PLAN

State, in the plan: the **prize** against the **blast radius** (law 29 — refuse
upside-down trades); the fix as **math** that reduces to stock at f=1; the
**acceptance test decided in advance**, with a positive control for any null it
relies on; and the **trap signature + revert** for each way it can go wrong.

Then work it **one item per build**, and verify from the log, not from optimism.

---

## 7. THE 1.5x-ONLY FAMILY

**A defect that is present at 1.5x and absent at 2x/3x tells you almost
nothing.** `Upscale2x.cs::ScaleDim` returns early at an integer factor and
`ScaleRound` is exact there, so *every* disagreement between two scalers is
1.5x-only by construction. Matching that pattern is the NULL HYPOTHESIS.

Work it in this order instead:

| step | question | instrument |
|---|---|---|
| 1 | **Is there a SIBLING THAT WORKS?** One broken of five identical controls is worth more than any instrument aimed at the broken one. Get eyes on the working sibling and the broken one together. | eyes |
| 2 | Do the two differ in **LEFT/TOP PARITY**? At f=1.5, `l*1.5` is integral only for even `l`. **ASK WHICH POPULATION THE CONTROL IS IN BEFORE ASKING ABOUT PARITY. (a) RUNTIME-SWEPT: `ScaleSubtree` is edge-derived for CONTAINERS ONLY. A LEAF (`GetChildCount()==0`) takes its EXTENT size-derived, `ScaleRound(w,f)`, logging `LEAFSIZE` (`UiSpike::ScaleSubtree`, grep `LEAFSIZE` or the `#148 THE REVERSE L` note), and the state-strip button class does the same (the `stripBtnClass` branch a few lines above it, grep `#167`) — so parity costs those no pixel of WIDTH. It still decides POSITION, which stays edge-derived for every window, leaves included (the same `#167` note states it: grep `Position edge-derived, size length-derived`). (b) PRE-SCALED: under a `kDataScaledSubtreeIds` root (for example the advisor strip `0x6A15C767`, the first entry in that array) `ScalePanelRoot` scales the ROOT and then RETURNS before the child loop (`UiSpike::ScalePanelRoot`, at its single `IsDataScaledSubtreeId` call site), so no descendant is ever swept and the parity rule there is the BUILDER's — `build_selective_safe.py::double_subtree_areas`, art-leaf = no children + `image=` + no `imagerect` (its `art_leaf` predicate, in `tools\selective-safe\build_selective_safe.py`). Nothing downstream repairs a number the builder writes.** | `gate_btn_undercover.py` |
| 3 | Does the control's **art cell** equal its scaled window? | `gate_btn_undercover.py` |
| 4 | **Look at it.** Composite the window offline from the shipped art. | `render_flyout.py` |
| 5 | Only then reach for the runtime blit code. | — |

### Levers, in ascending blast radius — PICK THE SMALLEST THAT WORKS

| lever | scope | verdict |
|---|---|---|
| change the **SIZE** of a leaf window (DLL, `GetChildCount()==0`) | that window | **The cure for the flyout-button case.** Nothing moves; ≤1px. |
| change a window's **POSITION** in a `.UI` | that `.UI` only | up to 2px at 1.5x. **Judge it in the densest grid it touches, not in the flyout that reported the bug.** Rejected in v2.94.0. |
| change **ART DIMENSIONS** | THE WHOLE GAME | Runtime-created strip items bind art by TGI and appear in NO `.UI`, so a builder-side conflict check is blind by construction. Rejected in v2.94.0. |

### Do not retry — all measured

- The runtime blit code for flyout buttons: both `BltClassThunk` blocks are
  gated on sizes those buttons never have. Six edits on a dead path.
- Bicubic/HQ resampling at fractional factors — it fringes the magenta colour key.
- Extending a short `imagerect` to its art — it broke the thumbnails twice, and
  the buttons that reported the bug carry no `imagerect` at all.
- "Cell must equal window" as a general law — 420 mismatches at 2x AND 3x on
  tiers that render correctly. Only ART-SIZED buttons are bound by it.

## 8. THE TEST RIG — getting a MOVABLE window

Eyes-on at a tier the display cannot reach, or dragging the window around to
test edges, needs THREE settings and only one of them belongs to this mod:

```
Apps\dgVoodoo.conf   FullScreenMode = false   <- THE ONE THAT MATTERS
                     CaptureMouse   = false   <- or the title bar is unreachable
SC4GraphicsOptions   WindowMode     = Windowed
                     WindowWidth/Height
SC4UIScale.ini       AutoScale=0 + ScaleFactor  (Set-Tier.ps1)
```

**`WindowMode=Windowed` ALONE DOES NOTHING.** dgVoodoo overrides it and the
game comes up borderless with no title bar. Every minute spent editing SC4's
ini while the wrapper says `FullScreenMode=true` is wasted. Both files must be
written **without a BOM**, and `dgVoodooCpl.exe` rewrites the conf if launched.

**Resolution is not the constraint it looks like.** Measured: the border is
present at 1024x768 *and* at 2400x1800 on a 2400x1600 desktop. A window taller
than the screen, and past DirectX 7's 2048 limit, still gets a border and still
drags — it just overhangs.

**Tier minimums** (`ScaleTier::Fits`, written-out table `kTierMinimums`):
1.5x → 1440x1080 · 2x → 1920x1440 · 3x → **2880x2160** (20% density headroom
over the 800x600 feel; 2x at 1920x1200 FAILS on height — a measured defect,
which is why the height is 1440, not 1200). With `AutoScale=0` a tier can be
forced below its minimum, which is how 3x is tested on a shorter screen;
height binds first, so breakage shows at the BOTTOM (the dock).

`Set-Tier.ps1` takes `-Tier 1|1.5|2|3`, and it sets the DATA as well as the
factor. **`-Tier 1` is the 1x baseline**: every package off and the stock font
restored, which a bare `ScaleFactor=1` edit does not do. Add `-Windowed`
(optionally `-Width W -Height H`, default 1024x768) and it writes both halves
of the window setting — dgVoodoo's conf and `SC4GraphicsOptions.ini` — in one
command. The screen is part of the tier: 1x at 3840x2160 is not a reference,
because every widget is then correct-but-tiny and formatting is the whole
question.
