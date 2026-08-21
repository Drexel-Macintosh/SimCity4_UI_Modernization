# The City Map Jump at City Load

The dock city map is the small map panel inside the main dock. Two symptoms
travel together when a city is opened with the UI scaler active:

- **The jump.** The dock and the city map inside it arrive at stock size and snap
  to the scaled size about a second into play, at the moment the reactive sweep
  reaches them.
- **The blank.** The map panel shows no map at all for the first seconds of play,
  and fills in the moment the load-warning modal is dismissed.

Stock is clean at the same resolution (2400x1600) with the mod's files renamed
aside, so both symptoms belong to the mod, not to the game.

## The blank: the repair destroys the picture

The blank is not written by anything. It is the mod's own surface recreate
erasing a good map.

Sampling the embedded render buffer at `[+0x114]` along a centre diagonal shows a
real map *before* the scaling pass (`distinct=4`, terrain colours `3D66B4` blue and
`73B000` green) and all zeros *after* the recreate. The recreate destroys the
display surface, builds a new one at the scaled size and pre-clears it to black, so
the map is gone until the engine's message-driven bake lands. That empty box is what
reads as corruption on screen.

The general rule: **when a repair is in the frame, check what the repair destroys
before hunting for what corrupts.** Six of the refuted mechanisms below ask what
writes the bad pixels. Nothing does.

## Cure: carry the picture across the recreate

1. Capture the old surface's pixels with `GetPixel` **before** the destroy.
2. Recreate at the new size with the destroy/create order **unchanged** — reordering
   those two steps is a known crash site.
3. Black-fill the new surface as the floor.
4. Repaint the captured picture, bilinear scaled.

The map stays visible, soft for one beat, then sharp once the engine's own bake
arrives.

## Cure for the jump: scale the dock early, in one action

The second half of the fix is to scale the dock from inside the `cGZWin::SetFlag`
detour — the game's own stack, which is still firing after city init returns — at the
moment the dock reports its full complement of 20 design children (see
`tools\research\CITY-DOCK-OVERLAP.md` section 1.4 for the child inventory). That lands
the dock at roughly +328ms and +109ms after load in measured runs, against +968ms for
the reactive sweep. The sweep then finds the dock already scaled, and the 1x-flash
instrumentation emits no line for it: scale and first paint are one action, which is
the only shape that removes a jump. Cadence tuning cannot, because a stock frame
still reaches the screen first.

The dock scale and the minimap surface recreate must likewise be **one action**
(`TryRecreateMinimapSurface`, the sweep's block used verbatim). Splitting them
crashes: a `blitSize` of 128 over a 64-wide one-shot surface is a heap overrun.

The early-dock path is configurable through `[UiSpike] EarlyDock` in the ini —
`0` off, `1` report when it would fire without acting, `2` perform the scale. The
compiled default is `1`. The tick runs once every 8 `SetFlag` calls and acts after 2
consecutive checks with an unchanged child count; the arm-to-sweep window is only
about 759ms and `SetFlag` traffic is scarce during the load tail, so a coarser
cadence never fires at all.

## Seven refuted mechanisms — do not re-derive

1. **Run the pass earlier via the message queue.** A posted `WM_APP` beats `WM_TIMER`
   by 15ms, because the game does not pump messages *at all* during the load tail.
   This kills `WM_TIMER` tuning, a show-hook, and `WM_APP` posting together.
2. **Data pre-scale the dock subtree.** Fixes the minimap and breaks every flyout:
   membership in `kDataScaledSubtreeIds` makes `ScalePanelRoot` return early, and the
   god-mode and mayor-mode flyout docking runs inside that child recursion.
3. **Data pre-scale the minimap alone.** Flyouts survive, but the map hangs outside
   the dock: the dock's rect is the **union of its children with no clamp**, so one
   overhanging pre-doubled child drags the anchored parent with it.
4. **Treat `[win+0x6c]` or vtable slots 92–93 as the pixel buffer.** `[+0x6c]` is the
   draw context, not a buffer. The slot list in `UiSpike.cpp` covering 87..97 is off
   by one and additionally mislabels two argument-taking slots as zero-arg. Never call
   a slot on a guess — the wrong arity corrupts the stack.
5. **Do the geometry inside `PostCityInit`.** It crashes at around 25 windows, even
   though two plain byte writes are safe at that point.
6. **Drive it off the stability-gate cadence.** That loses about 625ms, because
   `SetFlag` traffic is scarce during load.
7. **Blame the raster.** The raster is never the corrupt source; the repair is.

## `IsOnScreen` is not evidence about pixels

`IsOnScreen` is a pure `IsVisible()` flag walk: no rect test, no composition test, no
pixel test. A reading of `vis=1 onscreen=1` therefore says nothing about what is
painted, and cannot establish when a visual defect starts or stops. A pixel question
needs a pixel instrument.

For this defect the pixels settle it: the dock is the same size in the blank
screenshot and in the correct one, and the correct one is necessarily post-sweep, so
the blank state is post-sweep too.

## Structural constraint on the writers

After the scaling pass the display surface at `[+0xF0]` is provably all black — the
whole 128x128 is filled and logged every run. Any non-black pixels on screen after
that pass were written afterwards. The only writers are the transfers at `0x7A66F0`
and `0x7A67F0` and the bake at `0x7A7FF0`, all reachable only from `0x7A8640`, which
is **message-driven, not paint-driven**. That is the structural reason the blank
clears when the modal is dismissed: the message pump resumes and the bake finally
runs.

## Measured class offsets

Use these offsets rather than vtable slots:

| Offset | Meaning |
| --- | --- |
| `[+0xE4]` | blit size |
| `[+0xF0]` | display-surface **pointer** (one-shot `Init`) |
| `[+0x104]` | zoom |
| `[+0xFD]` / `[+0xFE]` | dirty flags |
| `[+0x114]` | **embedded** render buffer, built by `0x7A7570(this+0x114, w, h)` |

The minimap window has no art TGI (`clsid 0xca318388`, `winflag_pbuff=yes`), so the
usual "2x art inside a 1x window" failure mode is impossible for this widget. The
repair sequence itself succeeds on every run (`recompute 0x7A7840 ok zoom=0 fd=1
fe=1`); every size in that log is healthy, which is precisely why several readings of
it miss the bug. Fuller engine notes live in `tools\research\SC4-UI-ENGINE.md`.

## Guards in the shipped code

- **Minimap twin gate** — proves the instance being repaired actually descends from
  the dock, and prints the real parent id.
- **Bounded retry on all three surface blocks** — a latch that fires regardless of
  outcome leaves a faulted recreate permanently unretried, so the guard meant to
  prevent a crash makes that crash shape permanent instead.

## Method notes

- **Run the stock control before porting a cure to a lookalike symptom.** A very
  similar symptom — the dashboard minimap going blank on vehicle load — is the game's
  own bake latency, and reproduces in stock. Three measurements separate it from this
  defect without a build: the sweep reacts within 232ms while the symptom lasts
  seconds, so the timing lever cannot bite; the size-neutral carry-over is bit-exact
  identity, so nothing is blanked; and the symptom window has zero instrument
  coverage.
- **Matching a solved family is step one; step two is the new host's own
  constraints.** The rule "load-time damage is cured in data, never by a faster sweep"
  is correct, but the dock cannot take a data pre-scale, because its rect is an
  unclamped union of its children — a fact recorded in
  `tools\research\CITY-DOCK-OVERLAP.md`.
- **Probe first.** A log-only probe build risks nothing and can kill a theory
  outright; a build that changes behaviour risks a regression.
- **Watch for aliased sample points.** A probe sampling `p[n/4]` and `p[n/2]` on a
  64-wide buffer nearly hid the cause: those offsets are exact multiples of the pitch,
  so three of four samples land on column 0 and the reported "uniform grey" is the
  border, sampled repeatedly.

Related laws: `feedback-sc4-scaling-laws.md`, `feedback-null-is-not-evidence.md`,
`feedback-sc4-measure-dont-infer.md`, `feedback-sc4-blast-radius.md`,
`feedback-sc4-reactive-sweep-flashes.md`.
