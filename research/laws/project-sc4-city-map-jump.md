# The Dock Minimap at City Load

The dock minimap is the small city-map panel inside the main dock. When a city is
opened with the UI scaler active, it can appear corrupted for the first seconds of
play — not showing the region map, just garbage — and then correct itself the
moment the load-warning modal is dismissed. Stock is clean at the same resolution
(2400x1600) with the mod's files renamed aside, so the defect belongs to the mod,
not the game.

## Cause: the repair destroys the picture

The corruption is not written by anything. It is the mod's own surface recreate
erasing a good map.

Sampling the embedded render buffer at `[+0x114]` along a centre diagonal shows a
real map *before* the scaling pass (`distinct=4`, terrain colours `3D66B4` blue and
`73B000` green) and all zeros *after* the recreate. The recreate destroys the
display surface, builds a new one at the scaled size and pre-clears it to black, so
the map is gone until the engine's message-driven bake lands. That empty box is what
reads as corruption on screen.

The general rule: **when a repair is in the frame, check what the repair destroys
before hunting for what corrupts.** Six candidate mechanisms died first because every
one of them asked what writes the bad pixels. Nothing does.

## Cure: carry the picture across the recreate

1. Capture the old surface's pixels with `GetPixel` **before** the destroy.
2. Recreate at the new size with the destroy/create order **unchanged** — reordering
   those two steps is a known crash site.
3. Black-fill the new surface as the floor.
4. Repaint the captured picture, bilinear scaled.

The map stays visible, soft for one beat, then sharp once the engine's own bake
arrives.

## Cure: scale the dock early, in one action

The second half of the fix is to scale the dock from inside the `cGZWin::SetFlag`
detour — the game's own stack, which is still firing after city init returns — at the
moment the dock reports its full complement of 20 design children (see
`tools\research\CITY-DOCK-OVERLAP.md` section 1.4 for the child inventory). That lands
the dock at roughly +328ms and +109ms after load in measured runs, against +968ms for
the reactive sweep. The sweep then finds the dock already scaled and the flash
instrumentation emits no line for it.

The dock scale and the minimap surface recreate must be **one action**
(`TryRecreateMinimapSurface`, the sweep's block used verbatim). Splitting them
crashes: a `blitSize` of 128 over a 64-wide one-shot surface is a heap overrun.

The early-dock path is configurable; the compiled default is the conservative mode.

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

The claim "the corruption is present before the sweep" was an inference recorded as a
measurement, and it became the primary kill in six of the seven candidates above. Its
only support was `vis=1 onscreen=1` from `IsOnScreen`, which is a pure `IsVisible()`
flag walk with no rect test, no composition test and no pixel test. Screenshots of the
corrupt and correct states show the dock at the same size, and the correct one is
necessarily post-sweep, so the corrupt one is too. Any conclusion resting on
`IsOnScreen` about what is actually painted must be re-opened.

## Structural constraint on the writers

After the scaling pass the display surface at `[+0xF0]` is provably all black — the
whole 128x128 is filled and logged every run. Any non-black pixels on screen after
that pass were written afterwards. The only writers are the transfers at `0x7A66F0`
and `0x7A67F0` and the bake at `0x7A7FF0`, all reachable only from `0x7A8640`, which
is **message-driven, not paint-driven**. That is the first structural reason the
symptom clears when the modal is dismissed: the message pump resumes and the bake
finally runs. On its own that model predicts a black square, so it does not explain
coloured garbage.

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
fe=1`); every size in that log looks healthy, which is precisely why several readings
of it missed the bug. Fuller engine notes live in `tools\research\SC4-UI-ENGINE.md`.

## Hardening kept from this work

- **Minimap twin gate** — proves the instance being repaired actually descends from
  the dock, and prints the real parent id (the id asserted in the source comment was
  wrong).
- **Bounded retry on all three surface blocks** — they previously latched regardless
  of outcome, so a faulted recreate was never retried. The guard meant to prevent a
  crash was making that crash shape permanent.

## Method notes

- **Run the stock control before porting a cure to a lookalike symptom.** A second,
  very similar report — the dashboard minimap going blank on vehicle load — turned out
  to be the game's own bake latency, reproducible in stock. Three measurements killed
  the copy-paste reflex before any build: the sweep reacts within 232ms while the
  symptom lasts seconds, so the timing lever cannot bite; the size-neutral carry-over
  is bit-exact identity, so nothing was blanked; and the symptom window had zero
  instrument coverage. That closed in one ten-minute drive with no build at all.
- **Matching a solved family is step one; step two is the new host's own
  constraints.** The rule "load-time damage is cured in data, never by a faster sweep"
  is correct, but the dock cannot take a data pre-scale, because its rect is an
  unclamped union of its children — a fact already written down in
  `tools\research\CITY-DOCK-OVERLAP.md` and read without being applied.
- **Probe first.** Both log-only probe builds cost nothing and each killed a theory;
  both builds that changed behaviour shipped regressions.
- **Watch for aliased sample points.** A probe that nearly hid the cause sampled
  `p[n/4]` and `p[n/2]` on a 64-wide buffer. Those are exact multiples of the pitch,
  so three of four samples landed on column 0 and the reported "uniform grey" was the
  border, sampled repeatedly.

Related laws: `feedback-sc4-scaling-laws.md`, `feedback-null-is-not-evidence.md`,
`feedback-sc4-measure-dont-infer.md`, `feedback-sc4-blast-radius.md`,
`feedback-sc4-reactive-sweep-flashes.md`, `feedback-check-our-previous-work-first.md`.
