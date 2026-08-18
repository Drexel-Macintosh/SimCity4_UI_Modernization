---
name: reference-sc4-flyout-hittest-playbook
description: "THE cracked method for scaling clickable cGZWin menus (won on Disaster, built FOR Mayor mode) — router semantics, two-gate hit model, custom-override detection, dual-use fields, offline capstone+Unicorn workflow; full detail in HANDOFF \"REUSABLE PLAYBOOK\""
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-29T00:59:32.662Z
---

The complete method that cracked the Disaster flyout's clickable-area problem
(2026-07-28), distilled for reuse on Mayor-mode menus — which are built from the
same cGZWin machinery. **Full playbook + all addresses:
`SC4TouchControls/tools/research/HANDOFF-god-mode-flyouts.md` → "GOD MODE: DONE —
EVERY ISSUE AND EXACTLY HOW IT WAS FIXED" (top) and "REUSABLE PLAYBOOK".**

## FIRST: identify WHICH LAYER you are fighting (the master skill)

A menu is never one thing. Nearly every long thrash on this project was acting on
the wrong layer. Four independent layers, each identified differently:
- **Window tree** (position/size) — DumpTree/LiveDump; DPROBE logs only CHANGED
  rects per sweep, catching transitions a 1-second dump structurally cannot.
- **Draw** (what you see) — hook the buffer class Blt (vtable 0x00AC1400 slot 29)
  and correlate blit rect SIZE with the on-screen thing (94x62 = ring, 44x44 = a
  picture, tiles at d[0]>=200 = bar).
- **Hit-test** (what clicks) — a SEPARATE path (router → IsPointInMe → refined
  mask); hook slots 62/121/149 or disassemble the class's override.
- **Art** (pixels) — DBPF resources; refmap.csv + the dat builder report map
  script → TGI.

**The discriminator that works: change ONE thing and see what moves.** Hovering
moved only the bar → proof it was a separate window from the ring and pictures;
that one observation opened the whole flyout up. **If a layer won't respond to
your change, you are on the wrong layer.**

**The architecture every menu shares:**
- Router `GetChildWindowFromCursorPoint` 0x0099DFA9 (cGZWin base, ~90 classes):
  walks `[this+0x44]` children head-forward, skips !flag1 (invisible) and
  flag 0x200000 (input-transparent), FIRST child whose slot 40 claims the point
  wins, else self.IsPointInMe. **A closed upstream gate starves every
  downstream hook — a silent hook is NOT a broken hook.**
- Base IsPointInMe 0x0099C97C: coarse `[this+0x14]` rect → (if MouseTrans
  0x80000) transform slot 59 → refined slot 149 → `[this+0x64]` mask HitTest
  (2 args, inverted: 0 = opaque = clickable).
- Classes MAY override IsPointInMe (Disaster's container did: claim only the
  rightmost `[this+0xe0]` px). ALWAYS read the instance's vtable slots before
  assuming base behavior.
- **Dual-use fields:** container layout fields (0xe0..0xf4) can feed BOTH paint
  and hit-test. Scale for hit-test; mask back to 1x inside the draw-group hooks
  (SlotThunk 87..97 halve-on-entry/restore-after pattern).

**Why:** the Disaster bug was TWO intersecting gates (container claim ∩ strip
1x mask); every single-lever attempt failed and every downstream diagnostic was
silent, which mis-pointed at z-order for hours. The offline method found the
real gate in minutes of disassembly.

**How to apply (offline-first, usually no game launch):**
1. Log the instance vtable ptr → read slots 40/59/62/121/149/GetFlag.
2. capstone-disassemble any non-base slot (VA→file map via PE sections;
   template in `tools/flyout-sim/emu_hittest.py`).
3. Unicorn-emulate the REAL code, stubbing virtual calls with EXACT arg counts
   (a push with a matching pop after the call is a register SAVE, not an arg).
4. Chain stages, sweep x/y, REPRODUCE the observed bug first, then flip levers
   offline to find the minimal fix.
5. In-game fix = live-tunable ini levers + idempotent range-guarded writes.
6. Instruments already exist: DGP-OPEN/DCKIDS dumps (fire while open, enum
   order = router priority, per-child flags), DCLAIM, DS62/DXF, emu_hittest.py.
7. Verify slot argc before hooking (wrong argc = stack corruption crash);
   flag 0x200000 is the cheapest "make this window click-through" lever.

Related: [[project-sc4-god-flyouts]], [[project-sc4-ui-scaling-northstar]],
[[feedback-sc4-regression-net]]
