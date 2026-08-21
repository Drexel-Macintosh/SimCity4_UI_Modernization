# Hit-Testing Clickable cGZWin Menus

Scaling a menu so it *looks* right and scaling it so it *clicks* right are two
different jobs. The general method below applies to any of the game's flyout and
toolbar menus, because they are all built from the same `cGZWin` machinery.

## First: identify which layer you are on

A menu is never one thing. Acting on the wrong layer is the most common cause of
long, fruitless debugging. There are four independent layers, and each one is
identified by a different instrument:

| Layer | What it controls | How to observe it |
| --- | --- | --- |
| Window tree | Position and size | Tree dumps and live dumps. A per-sweep log of *changed* rects catches transitions that a once-per-second full dump structurally cannot. |
| Draw | What appears on screen | Hook the buffer class `Blt` (vtable `0x00AC1400`, slot 29) and correlate blit rect size with the on-screen element — e.g. 94x62 is the ring, 44x44 a picture, tiles with `d[0] >= 200` the bar. |
| Hit-test | What responds to clicks | A separate path entirely: router → `IsPointInMe` → refined mask. Hook slots 62/121/149, or disassemble the class's own override. |
| Art | The pixels themselves | DBPF resources; resolve through the reference map and the archive builder's report to a TGI. |

The discriminator that works is to **change exactly one thing and see what
moves.** Elements that move independently under a single hover or a single
geometry change are separate windows; elements that move together share a
parent. One such observation partitions an entire flyout into its real windows
in a single pass. Conversely, if a layer refuses to respond to a change, the
change is on the wrong layer.

## The architecture every menu shares

**Router — `GetChildWindowFromCursorPoint` at `0x0099DFA9`** (on the `cGZWin`
base, shared by roughly 90 classes). It walks the child list at `[this+0x44]`
head-forward, skipping any window whose flag 1 is clear (invisible) and any with
flag `0x200000` (input-transparent). The *first* child whose slot 40 claims the
point wins; if none claims it, the window's own `IsPointInMe` decides.

The consequence is the single most important debugging fact here: **a closed
upstream gate starves every downstream hook.** A hook that logs nothing is not
evidence of a broken hook — the identical silence comes from a hook the walk
never reaches, because something earlier in the walk already claimed the point
or the window was skipped outright.

**Base `IsPointInMe` at `0x0099C97C`** implements a two-gate hit model:

1. Coarse rect test against `[this+0x14]`.
2. If the MouseTrans flag `0x80000` is set, transform through slot 59.
3. Refined test through slot 149.
4. Final mask `HitTest` through `[this+0x64]` — two arguments, and **inverted**:
   a return of 0 means opaque, which means clickable.

Both gates must pass. A bug caused by two intersecting gates — a container that
claims only part of its area, intersected with a hit mask still at 1x — is
immune to every single-lever fix, and every diagnostic downstream of the first
closed gate stays silent while it happens. That silence is easily mistaken for a
z-order problem.

**Classes may override `IsPointInMe`.** One container in the disaster flyout does
exactly this: it claims only the rightmost `[this+0xe0]` pixels of its rect.
Always read the actual instance's vtable slots before assuming base behavior.

**Dual-use fields.** Container layout fields in the `0xe0..0xf4` range can feed
both the paint path and the hit-test path. The workable pattern is to scale them
for hit-testing and mask them back to 1x inside the draw-group hooks — the
halve-on-entry / restore-after-return pattern used in slot thunks 87 through 97.

## Applying it, offline first

Most of this work needs no game launch.

1. Log the instance's vtable pointer, then read slots 40, 59, 62, 121, 149, and
   `GetFlag`.
2. Disassemble any non-base slot with Capstone. Map virtual address to file
   offset via the PE section table; there is a working template in
   `tools/flyout-sim/emu_hittest.py`.
3. Emulate the real code with Unicorn, stubbing virtual calls with the **exact**
   argument counts. A push followed by a matching pop after the call is a
   register save, not an argument — miscounting here produces plausible garbage.
4. Chain the stages together, sweep x and y, and **reproduce the observed bug
   offline before changing anything.** Only then flip levers to find the minimal
   fix.
5. Ship the in-game fix as live-tunable ini levers with idempotent,
   range-guarded writes.
6. Verify a slot's argument count before hooking it. The wrong argc corrupts the
   stack and crashes.
7. Flag `0x200000` is the cheapest available lever for "make this window
   click-through" — it removes a window from the router walk without touching
   its geometry or its art.
