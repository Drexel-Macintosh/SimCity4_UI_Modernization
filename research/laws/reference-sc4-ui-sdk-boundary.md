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

## The triage test — run it before the first patch

For any element whose owner is unknown, ask three questions:

- **(a)** Does it ever appear as a window in a full-depth live tree dump? Test
  both visibility flips and newly-created windows.
- **(b)** Does it have art in any dat?
- **(c)** Does it span or overlay the 3D view?

Three scores decide the element's category:

- **(a) no, (b) no, (c) yes** — wholly outside the GZWin layer. Nothing in the
  toolkit reaches it. Record the negatives and move on.
- **(a) no, (b) yes, (c) yes** — the mixed case: art reachable, geometry not.
  See the section below.
- **(a) yes** — a real window, whatever (b) and (c) say. The sweep, the `.UI`
  pass and the art overrides all apply.

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

An element scoring **(a) no, (b) yes, (c) yes** sits between the two clean
answers — never a window, drawn over the 3D view, yet its art *is* a dat
resource that can be staged. It differs from the wholly-outside case in (b)
alone, and that single difference is what makes it look curable when it is only
half curable.

In that case the larger art genuinely loads (an art-fetch probe confirms the
fetch), and the renderer then draws it at a size it computes itself, resampling
it back down. The result on screen is pixel-identical to stock, which reads as a
staging failure and is not one. The confirmed instance is the "move in a sim"
marker over the city view: its portrait art is reachable, its geometry is not.

Before staging bigger art for anything drawn over the 3D view, establish which
half of the pair is actually reachable. The only cure for this category is a
size constant in the renderer's own path — the same class of lever as the
signpost and offer-balloon constants, but inside the module that owns the
element. The module owning a resource is often not the module drawing it: for
the marker, the portrait preload sits at `0x00775239` in a `0x0077xxxx`
subsystem, while the billboard builder repeatedly targeted by window-layer
attempts lives at `0x0046Cxxx`.

Two related traps sit in the same area. A fetch probe cannot find a cached
consumer: a load-time hook answers "who owns this", never "who is drawing it
right now", so before arming an instrument establish whether the thing being
hunted passes that point every time or only once. And staging bigger art can
break a consumer that hard-codes a power-of-two texture side — a 36x41 to 72x82
stage crosses the 64 to 128 boundary and halves the UVs of anything dividing by
a baked-in `64`. That break appears only at the tier that crosses the boundary,
which reads as a tier mystery rather than an art change. Ask who divides by the
art's size.

## History: two elements once wrongly called outside the boundary

**No element of the shipped UI is currently known to sit outside the
boundary.** These two were carried in this file as confirmed outside-the-
boundary examples; both are now confirmed windows, and the finding below
supersedes the two bullets that used to stand here.

- **The paused / sim-speed screen-edge border and corner badge.** It IS a
  window — `cSC4WinAlertBorder`, id `0x6A5E44B6`, vtable `0x00AB5B48` — born
  full-screen and *never flipping visibility*, which is exactly why a
  visibility probe could never fire on it. Art ships as three 120x120 sheets
  (`0x14315E60/61/62`); its own 9-slice drawer is `0x008D9550` (exactly one
  caller), distinct from the busy `0x008D8800` that serves `GZWinBMP`'s
  `edgeimage=yes` path and `GZWinBtn`. Six probes and an art decode had come
  back negative — every one of them was a visibility/render-side check, and
  none could have fired on a window that never toggles visible. See
  `tools\research\SC4-UI-ENGINE.md` §0, §4.6c.
- **The doubled Mayor Rating bar in the region city-select bubble.** It IS a
  window — `clsid=0xAA5D16A9` (`cSC4WinAuraBar`), `id=0x4A553000`, declared
  102x11 in `I-ca539340` at depth 3 — cured as a data change. Two nulls had
  put it outside, and neither carried a positive control: an `RGKID` dump
  that stopped one level above the bar, and an A/B with
  `RatingArrowPatch=0` that tested the HUD controller (`0x7E86C0-0x7E8A80`),
  a different class with different art that was never involved. See
  `tools\research\SC4-UI-ENGINE.md` §0.

**Why the mistake happened both times:** every instrument used to place
these outside the boundary was structurally incapable of seeing an
inside-the-boundary element in the first place — a visibility flip on a
window that is born visible and never changes, and a tree dump that stopped
one depth short paired with an A/B run against the wrong class entirely. A
null from an instrument that could not have seen the thing is not evidence
the thing is outside the boundary; see the house laws `NULL IS NOT EVIDENCE`
and `TWO BLIND INSTRUMENTS AGREEING = ONE`. The boundary table was wrong
twice on exactly this failure mode before either was corrected.

## The one lever that reaches the render path

Everything visible must pass through the DirectDraw primary surface, so hooking
its `Blt` / `BltFast` is the single lever that can see render-path elements. It
is a separate subsystem, and it runs through the dgVoodoo wrapper that the
working scaled setups depend on, so such a hook stays gated off by default,
log-only, with a revert path.

Weigh the cost against the prize before starting. History argues for
weighing hard: both of this file's prior candidates for this lever (above)
turned out to be ordinary windows once tested with an instrument capable of
seeing them, so the render-path lever has never yet been the correct one for
a shipped-UI element.

Canonical narrative: `tools\research\SC4-UI-ENGINE.md` §0, "THE BOUNDARY OF THIS
SDK".
