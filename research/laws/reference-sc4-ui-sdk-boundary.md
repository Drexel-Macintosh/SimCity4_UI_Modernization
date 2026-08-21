# The GZWin Boundary

Not everything on screen is a window. Every lever this class of mod has — the
runtime window sweep, the `.UI` data pass, art overrides, buffer and draw hooks —
reaches only the `cIGZWin` / GZWin UI layer. Some visible elements are painted
in the render/present path instead, and no amount of window-side work can touch
them. Knowing which side of that line an element sits on is the first question,
not the last.

## The structural fact: the UI buffer class never composites to the screen

With the class-level `Blt` hook armed, every destination observed was
panel-sized — 258x482, 383x156, 360x156, 340x148, 323x156, 317x148, 280x148 —
and none was screen-sized. The consequence is permanent: a blit-level hook on
that buffer class can never see a full-screen element, so a zero result from it
is structural, not evidence. Any probe built on that hook needs a stated
positive control before its silence means anything.

## The triage test — run it before the first patch, not after the fourth

For any element whose owner is unknown, ask three questions:

- **(a)** Does it ever appear as a window in a full-depth live tree dump? Test
  both visibility flips and newly-created windows.
- **(b)** Does it have art in any dat?
- **(c)** Does it span or overlay the 3D view?

If (a) is no, (b) is no, and (c) is yes, the element is outside the GZWin layer.
Record the negatives and move on.

"Is this even a window?" is answered by one ten-second launch with a full-depth
dump running, and the answer eliminates or confirms the entire toolkit at once.
Choosing between candidate addresses in a disassembler is wasted effort if the
correct answer is "none of them — it is not in the window layer at all."

A dump used this way must carry its own positive control. A worked example: 37
ticks at 1000 ms with the target element deliberately left on screen produced
623 ids present in all of the last eight ticks and zero new ids versus the first
five — the tree was identical with the element up and with it down. The control
that made that null trustworthy was a transient window opened in the same
session: a picker dialog and its grid appeared in exactly one tick, 88 transient
ids captured. The instrument could see transient windows; it simply never saw
this one.

## The third category: art reachable, geometry unreachable

The triage test above assumes an element is wholly in or wholly out. There is a
middle case that scores (a) yes and (c) yes but (b) **no** — never a window,
drawn over the 3D view, yet its art *is* a dat resource that can be staged.

In that case the larger art genuinely loads (an art-fetch probe confirms the
fetch), and the renderer then draws it at a size it computes itself, resampling
it back down. The result on screen is pixel-identical to stock, which reads as a
staging failure and is not one. The confirmed instance is the "move in a sim"
marker over the city view: its portrait art is reachable, its geometry is not.

Before staging bigger art for anything drawn over the 3D view, establish which
half of the pair is actually reachable. The only cure for this category is a
size constant in the renderer's own path — the same class of lever as the
signpost and offer-balloon constants, but inside the module that owns the
element. Note that the module owning a resource is often not the module drawing
it: for the marker, the portrait preload sits at `0x00775239` in a `0x0077xxxx`
subsystem, while the billboard builder repeatedly targeted by window-layer
attempts lives at `0x0046Cxxx`.

Two related traps in the same area. A fetch probe cannot find a cached consumer:
a load-time hook answers "who owns this", never "who is drawing it right now",
so before arming an instrument ask whether the thing being hunted passes that
point every time or only once. And staging bigger art can break a consumer that
hard-codes a power-of-two texture side — a 36x41 to 72x82 stage crosses the
64 to 128 boundary and halves the UVs of anything dividing by a baked-in `64`.
That break appears only at the tier that crosses the boundary, which reads as a
tier mystery rather than an art change. Ask who divides by the art's size.

## Known outside the boundary

- **The paused / sim-speed screen-edge border and corner badge.** Drawn in raw
  screen pixels — roughly a 2-3 px frame and a ~24 px badge — at every tier.
  Six independent probes plus an offline decode of the art all came back
  negative on the window layer.
- **The doubled Mayor Rating bar in the region city-select bubble.** An A/B
  comparison established the executable's own painter draws it.

## The only remaining foothold

Everything visible must pass through the DirectDraw primary surface, so hooking
its `Blt` / `BltFast` is the one lever that can see render-path elements. It is
a new subsystem, and it runs through the dgVoodoo wrapper that the working
scaled setups depend on, so it should be gated off by default, log-only, with a
revert path.

Weigh the cost against the prize before starting. For the sim-speed border, the
prize is a 2 px line.

Canonical narrative: `tools\research\SC4-UI-ENGINE.md` §0, "THE BOUNDARY OF THIS
SDK".
