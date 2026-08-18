---
name: reference-sc4-runtime-image-lever
description: "SC4 UI scaling — the GZWinBMP draw hook (class 0x00ADF6A0) is THE lever for any image the game supplies at runtime; scoping it is an id list, and the fit clamp gives the tier factor with no tuning constant."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-02T18:44:08.283Z
---

**THE LEVER for every "image draws 1x in the top-left of a doubled window"
defect** (portraits, pickers, mission markers — the class in task #47):
`kBmpClassVt = 0x00ADF6A0`, slot 88 `= 0x009BC325`, hooked per instance onto
ONE shared patched vtable copy (`gBmpVtCopy`), with `BmpCtxBltThunk` scaling
the plain-path DEST rect. `src\UiSpike.cpp`.

**Why it lands on the tier factor with NO tuning constant:** the plain path
makes the draw follow the **SOURCE** —
`dst = {areaL, areaT, areaL+srcW, areaT+srcH}`, the window rect is never read —
so 32px art draws 32px inside a 128px window. The thunk scales the dest by the
tier factor and then **reduces it until it still fits the live window**.
64x64 inside 128x128 fits ⇒ exactly 2x, and **overshoot is structurally
impossible**. An already-correct 2x image clamps to 1.0, so two fixes can never
fight. Never add a multiplier here — change the scope instead.

**SCOPING IS THE WHOLE GAME, and it is an ID LIST.** `HookRuntimeBmpsUnder`
walks GZWinBMPs under listed ROOT ids (`kBmpxCityRoots` / `kBmpxDialogRoots`).
Two traps, both paid for on 2026-07-30:
1. **A window that parents straight to the 3D view is under NO root** and is
   never walked. The U-Drive-It mission marker `0x48E945B4` was reachable by
   this hook the whole time; adding its id was the entire fix (v2.36.6,
   user-confirmed). Add the id of the window ITSELF — the root is hooked too.
2. **TRANSIENT windows** (the marker is PRESENT in one probe sample and gone
   0.5 s later) defeat every static/one-shot approach. The sweep re-finding it
   by id each tick is what makes it stick.

**EDGE mode is excluded on purpose** (flag bit 8 on the holder at `[this+0xd8]`):
it 9-slices with many blits and scaling those would shear the frame.

**Positive identification is enforced** (`HookBmpInstance`): class vtable AND
slot-88 target are both verified, and a FlashGuard thunk in slot 88 is accepted
so the chain stays intact. Hooking by class alone is what killed the game on
Earned Cars (law 3).

**⚠ INSTALLING THE HOOK IS ONLY HALF OF IT — THE ENGINE MUST CALL IT**
(2026-08-02, #47 CLOSED v2.42.4, user-confirmed *"fixed 100%"*). The My Sims
portraits were intermittently 1x with the hook **fully installed**: on a
failing open the log read `25 instance(s) hooked` and then a per-open census
of `scaled=0` — our Draw was **never called** in 13 seconds on screen. The
engine paints some opens through a non-Draw path, so the cell shows whatever
its private buffer holds (these cells are `winflag_pbuff=yes`).
**Cure: kick ONE `InvalidateSelfAndParents()` through each freshly hooked
LEAF, once per open** — the ROOT alone does not reach them (root-only was
Qwen's v2.42.2 = "less frequent but still happening"). Bounded, capped at 64
with a saturation line; NOT ghost-heal (which was blind repeated sweeps).
**Acceptance instrument to reuse: a per-open census of COUNTS**
(`BMPX open #N ... census: scaled=X clamped=Y`) — counts cannot saturate the
way a log-line budget can, so a failing event always leaves a line. See
[[feedback-sc4-scaling-laws]] law 41.
⛔ Dead here, do not re-derive: single-find/hidden-template (the root
resolves to a NEW pointer every open); "our doubling enlarged the source
rect" (`imagerect` correctly untouched); **born-2x data** — it was the
PRE-COMMITTED cure and the measurement killed it, because these cells are
already born 2x (the gauge precedent needs windows born 1x).

**Still open in this class:** the U-Drive-It gauge dials (custom class
`0xCBCBF1E0` — code-paints into its OWN cached buffer, so the lever there is
force-recreate-buffer, not this one; ⚠ that prescription rests on the
CONTESTED `[win+0x6c]` claim — measure before building on it) and the Graphs
chart interior.

Related: [[feedback-sc4-measure-dont-infer]], [[feedback-sc4-scaling-laws]],
[[project-sc4-ui-scaling-northstar]].
