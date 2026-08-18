---
name: project-sc4-city-map-jump
description: "SC4 task #89 CLOSED v2.41.19 (2026-08-01, user-confirmed): dock never seen at 1x, map never corrupted. Fix = carry-over (our recreate was erasing a good map) + EARLYDOCK (SetFlag-detour scale at full design child count, surface recreate in the SAME action). Seven dead ends documented."
metadata:
  node_type: memory
  type: project
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-02T01:43:05.727Z
---

**User's words (he CORRECTED my model and it mattered):** on city open the dock
minimap shows **CORRUPTION** — *"just corruption, not the region [map]"* — and
*"it should be loading into [the correct city map] directly"*. It fixes itself
when he dismisses the load-warning modal. My first model ("region image, then
city image") was wrong and sent me down two bad paths.

**SEVEN REFUTED MECHANISMS — never re-derive** (5-7: geometry inside
`PostCityInit` crashes at ~25 windows though two byte writes are safe there;
the stability-gate cadence loses 625ms because SetFlag is scarce during load;
the raster was never the corrupt source — our recreate was):
1. **Run the pass earlier via the message queue.** Posted `WM_APP` beat
   `WM_TIMER` by **15ms**; the game does not pump messages AT ALL during the
   load tail. Kills `WM_TIMER` tuning, `ShowHook` and `WM_APP` together.
2. **Data pre-scale the dock SUBTREE.** Fixed the minimap, **broke every
   flyout**: `kDataScaledSubtreeIds` makes `ScalePanelRoot` RETURN EARLY and
   the god/mayor **flyout docking runs inside that child recursion**.
3. **Data pre-scale the minimap ALONE.** Flyouts fine, **map hung outside the
   dock**: the dock's rect is the **UNION of its children with no clamp**, so
   one overhanging pre-doubled child drags the anchored parent.
4. **`[win+0x6c]` / vtable slots 92–93 as the pixel buffer.** `[+0x6c]` is the
   **draw context**; `UiSpike.cpp`'s own slot list (87..97) is **off by one**
   and also mislabels two arg-taking slots as zero-arg. Never call a slot by
   guess — wrong arity corrupts the stack.

## ✅ SEQUEL #91 CLOSED NOT-A-BUG (2026-08-02, same day)

The vehicle-load dashboard minimap blank is **the game's own bake latency —
stock does it too** (stock control, user-confirmed same day). Three plan-mode
measurements killed the copy-paste reflex first: the sweep reacts within
<=232 ms (symptom is seconds, so #89's timing lever can't bite); our
size-neutral carry-over is bit-exact identity (we never blanked it); and the
whole symptom window had zero instrument coverage. ⚠ The lesson: when a
symptom "matches a solved family", run the STOCK CONTROL before porting the
cure — #91 closed in one 10-minute drive with no build. Full record:
`_tests/REGRESSION.md` #91.

## ✅✅ CLOSED v2.41.19 — user: *"It loaded perfectly and I think it's fixed"*

Second half: **EARLYDOCK**. The dock is scaled from inside the
`cGZWin::SetFlag` detour — the game's own stack, still firing after city init
returns — the moment it reports its full **20 design children**
(`CITY-DOCK-OVERLAP.md` 1.4). Measured **+328ms / +109ms** vs the sweep's
+968ms; the sweep then finds it AlreadyScaled (ScaleAll 456→431; both +73
since v2.42.0 — 504 healthy — after #90 put the style panel in the city
pass), and FLASHSET
emits **no line** for the dock any more. Scale + minimap surface recreate are
**ONE action** (`TryRecreateMinimapSurface`, the sweep's block extracted
verbatim) — splitting them was the v2.41.15 crash (blitSize 128 over a 64
one-shot surface = the v2.21.0 heap overrun). Two cities in one session, both
clean. Live: `EarlyDock=2`; compiled default 1. Law 39 minted.

## ✅ CAUSE FOUND 2026-08-01 (v2.41.12/.13) — user-confirmed *"soft image then full, it's getting better"*

**OUR OWN REPAIR WAS THROWING THE MAP AWAY.** Measured by sampling the raster
`[+0x114]` on a centre diagonal: **before** our pass it holds a real map
(`distinct=4`, terrain colours `3D66B4` blue / `73B000` green); **after** our
recreate it is all zeros. We destroyed the display surface, built a new one and
**pre-cleared it to black**, so the map vanished until the engine's
message-driven bake landed — and that empty box is what read as "corruption".

**THE FIX:** carry the picture across the recreate — capture the old surface's
pixels (`GetPixel`) BEFORE the destroy → recreate at the new size with the
**destroy/create order UNCHANGED** (v2.21.1 crash site) → black-fill as the
floor → repaint the captured picture **bilinear** scaled. Map stays visible;
soft for one beat, then sharp.

**WHY SIX MECHANISMS DIED FIRST:** every one asked *what writes the bad pixels*.
Nothing did. See [[feedback-sc4-scaling-laws]] law 35 — **when a repair is in
the frame, check what the repair DESTROYS before hunting for what corrupts.**
And law 36: the probe that nearly hid it sampled `p[n/4]`/`p[n/2]` on a 64-wide
buffer, which are exact multiples of the pitch, so three of four samples were
column 0 — "uniform grey" was the border, sampled repeatedly.

**⛔ RETRACTED — I recorded an INFERENCE as a MEASUREMENT.** "The corruption is
present BEFORE our sweep" was never measured: its only evidence is
`vis=1 onscreen=1` from `IsOnScreen`, a **pure `IsVisible()` flag walk** with no
rect, composition or pixel test. It then became the primary kill in six of seven
candidate mechanisms. And our own record contradicts it — both user screenshots
show the dock at the SAME size, and the correct one is necessarily post-sweep,
so the corrupt one is too. **Re-open everything killed on that test.**

**NEW HARD CONSTRAINT:** after our pass the display surface `[+0xF0]` is
**provably all black** (we Fill the whole 128x128, logged every run). So if the
corrupt pixels are on screen after our pass, something wrote non-black AFTER our
Fill. The only writers (`0x7A66F0`/`0x7A67F0` transfers, `0x7A7FF0` bake) are
reachable only from `0x7A8640`, which is **MESSAGE-driven, not paint-driven** —
the first structural reason "corrects when the modal is dismissed" could be
causal. On its own it predicts a BLACK square, and the user reports colour.

**ESTABLISHED (measured):** stock is CLEAN at the same 2400x1600 with our files
renamed aside, so the defect is **ours**; the minimap has **no art TGI**
(`clsid 0xca318388`, `winflag_pbuff=yes`) so 2x-art-in-1x-window is impossible
for it; and our repair sequence **succeeds** every run (`recompute 0x7A7840 ok
zoom=0 fd=1 fe=1`). Every size in that log looks healthy — which is exactly why
four readings of it missed the bug.

**Measured class offsets** (use these, never vtable slots): `[+0xE4]` blitSize,
`[+0xF0]` display-surface POINTER (one-shot `Init`), `[+0x114]` **embedded**
render buffer (`0x7A7570(this+0x114,w,h)`), `[+0x104]` zoom, `[+0xFD]/[+0xFE]`
dirty flags. Full entry: `SC4-UI-ENGINE.md` ~:310.

**Shipped and kept:** the minimap **twin gate** (proves the instance descends
from the dock; prints the parent id the comment had falsely claimed since
v2.22.3) and **bounded retry** on all three surface blocks (they used to latch
regardless of outcome, so a faulted recreate was never retried — the v2.21.0
crash shape made permanent by the guard meant to prevent it).

**THE PROCESS LESSON:** the symptom matched a solved family (advisor faces #43:
load-time damage is cured in DATA, never by a faster sweep) and I applied that
cure without checking whether THIS container could take it —
`CITY-DOCK-OVERLAP.md` already documented the union rect, and it was read and
not applied. Matching the family is step one; **step two is the new host's own
constraints.** Also: both log-only probe builds cost nothing and killed a
theory each, while both builds that changed behaviour shipped regressions —
**probe first**.

Full write-up: `_tests/REGRESSION.md` "CITY-OPEN CORRUPTED MINIMAP" and the top
of `HANDOFF.md`. Related: [[feedback-sc4-scaling-laws]],
[[feedback-check-our-previous-work-first]], [[feedback-null-is-not-evidence]],
[[feedback-sc4-measure-dont-infer]], [[feedback-sc4-blast-radius]],
[[feedback-sc4-reactive-sweep-flashes]].
