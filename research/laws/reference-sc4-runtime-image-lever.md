# The GZWinBMP Draw Hook

The lever for every "image draws at 1x in the top-left corner of a doubled
window" defect — portraits, pickers, in-world markers, any bitmap the game
supplies at runtime rather than loading from a `.UI`-declared asset.

## The hook

- Class vtable: `kBmpClassVt = 0x00ADF6A0`
- Draw slot: 88, stock target `0x009BC325`
- Implementation: `src\UiSpike.cpp`

Each instance is repointed onto **one shared patched vtable copy**
(`gBmpVtCopy`) rather than being patched in place. A single copy keeps every
hooked instance on the same code path, makes install idempotent, and avoids
writing to the class vtable itself (which would capture instances that must not
be touched).

The patched slot is `BmpCtxBltThunk`, which scales the destination rect of the
**plain** blit path.

## Why it lands on the tier factor with no tuning constant

On the plain path the engine derives the destination from the **source**:

```
dst = { areaL, areaT, areaL + srcW, areaT + srcH }
```

The window rect is never read. That is exactly why 32 px art draws 32 px inside
a 128 px window.

The thunk scales that destination by the tier factor and then **reduces it
until it still fits the live window**. 64x64 inside 128x128 fits, so the result
is exactly 2x; an image that is already correct at 2x reduces back to 1.0 and is
left alone. Two independent fixes for the same widget therefore cannot fight,
and **overshoot is structurally impossible** — the fit reduction is bounded by a
measured window, not by a guessed constant.

Never add a multiplier here. If a widget scales wrongly, the scope is wrong, not
the factor.

## Scoping is the whole problem, and it is an id list

`HookRuntimeBmpsUnder` walks GZWinBMP instances beneath listed root ids
(`kBmpxCityRoots` for the city UI, `kBmpxDialogRoots` for dialogs). Two traps:

1. **A window that parents straight to the 3D view sits under no root** and is
   never walked, no matter how many ancestors are listed. Such a window is
   already reachable by this hook; the entire fix is adding the id of the window
   **itself** to the list, because a listed root is hooked as well as walked.
   One in-world marker (`0x48E945B4`) sat unfixed for a long time for exactly
   this reason.
2. **Transient windows** defeat every static or one-shot install: the window is
   present in one probe sample and gone half a second later. The periodic sweep
   re-finding the window by id each tick is what makes the hook stick.

## Edge mode is excluded on purpose

Flag bit 8 on the holder at `[this+0xd8]` selects a 9-slice edge draw composed
of many separate blits. Scaling those blits individually shears the frame, so
edge-mode holders are skipped and left to the 9-slice art path.

## Positive identification is enforced

`HookBmpInstance` verifies **both** the class vtable and the current slot-88
target before touching an instance. A FlashGuard thunk already sitting in slot
88 is accepted so an existing chain stays intact.

Hooking by class alone crashes the game — the Earned Cars reward path shares the
class with instances whose draw slot has been replaced, and blindly overwriting
it breaks the chain.

## Installing the hook is only half of it — the engine must call it

A fully installed hook can still produce 1x images intermittently. The failure
signature is a log reading `25 instance(s) hooked` followed by a per-open census
of `scaled=0`: the patched Draw was never invoked at all. The engine paints some
opens through a non-Draw path, and the cell then shows whatever its private
buffer already holds. Cells that behave this way carry `winflag_pbuff=yes`.

Cure: kick one `InvalidateSelfAndParents()` through each freshly hooked **leaf**
once per open. Invalidating the root alone does not reach the leaves — it
reduces the failure rate without eliminating it, which is the classic shape of a
partially-correct invalidation. The kick is bounded and capped (64 per open,
with a saturation line) rather than a repeated blind sweep.

**Acceptance instrument:** a per-open census of counts, e.g.
`BMPX open #N ... census: scaled=X clamped=Y`. Counts cannot saturate the way a
per-line log budget can, so a failing event always leaves evidence behind.

## Dead ends in this class — do not re-derive

- **Single-find or hidden-template caching.** The root resolves to a new pointer
  on every open, so any cached handle is stale on the second open.
- **"The doubling enlarged the source rect."** It does not; `imagerect` is
  correctly untouched by this path.
- **Born-2x data.** These cells are already born at 2x, so pre-scaling the data
  changes nothing. The born-2x precedent only applies to windows that are born
  at 1x.

## Adjacent classes this hook does not cover

Custom classes that code-paint into their own cached buffer (for example
`0xCBCBF1E0`) are not reachable through this slot; the lever there is forcing a
buffer recreate, not scaling a blit destination. Chart interiors drawn entirely
by the renderer are likewise outside this hook's reach.
