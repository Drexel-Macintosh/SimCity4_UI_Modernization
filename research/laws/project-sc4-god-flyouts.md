---
name: project-sc4-god-flyouts
description: "SC4 god-mode flyouts — all five at 2x since v2.11.30, BUT ⚠ 'COMPLETE' was overstated: Disaster stayed on MECHANISM GENERATION 1 and still jumped/flashed on open until v2.39.4 (2026-07-31), which moved it to born-at-Place. Clicks/junction/dock from the v2.11.x work are still correct + confirmed. EVERY issue + how it was diagnosed is in HANDOFF-god-mode-flyouts.md 'GOD MODE: DONE'; the generation ledger is tools\\research\\MECHANISM-GENERATIONS.md"
metadata:
  node_type: memory
  type: project
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-31T22:41:42.812Z
---

God-mode tool flyouts for the SC4 UI-scaling northstar. **Pickup docs, in
order: `SC4TouchControls/tools/research/HANDOFF-god-mode-flyouts.md`
("REUSABLE PLAYBOOK" + "GATE FOUND + FIX" sections) then
`GOD-MODE-FLYOUTS.md` (full history/dead ends).**

**2026-07-29 — still COMPLETE + LOCKED, but four LATER LAWS generalise the
mechanisms here** (see [[feedback-sc4-scaling-laws]] and the new "⚠ LATER LAWS"
block at the top of HANDOFF-god-mode-flyouts.md). Most relevant to this work:
the alignment-marker rule has a DATA-side twin — scaling a marker inside a
shipped `.UI` displaced a whole panel by exactly `−markerOffset` — and any art
fix here can be silently shadowed by another mod in a subfolder (LOAD-ORDER
LAW). The height-based container gates were also re-cut to an EXACT width
after they missed menus twice.

**✅ STATUS (2026-07-28, v2.11.25-dualuse USER-CONFIRMED): ALL FIVE FLYOUTS
DONE.** Terraform, Terrain-FX, Day/Night (shares Terrain-FX's window), and
Disaster — the hardest — is fully working at 2x: bar/ring/pictures scaled,
layering Circle→Strip→Pictures, 9-item scroll with working arrows, hover-jump
fixed, and FULL-WIDTH CLICKS ("YOU DID IT!" — single bar + left clicks
confirmed in-game).

**HOW THE CLICK FIX WORKS (the crack, found by offline disasm/emulation — full
method in [[reference-sc4-flyout-hittest-playbook]]):**
- The container class (vt 0x00AB6AA8) OVERRIDES IsPointInMe (0x0079A180 →
  slot 121 = 0x0079AE30): claims only `local_x >= width - [this+0xe0]` — the
  rightmost [0xe0] px. [0xe0] held its 1x value (53) while the draw was 2x →
  only the right half clicked; every downstream hook (DS62/DS149) was silent
  because the router's first-claim-wins starved them (NOT z-order, NOT a rect).
- Fix = ini [Disaster] **ClaimScale=2** (dock loop doubles [container+0xe0],
  idempotent 30..60 guard, DCLAIM log) + **SelForce=1** (gVtCopy2[149] opens
  the strip's 1x refined mask — both gates intersect, both levers required).
- **[0xe0] is DUAL-USE** (claim width AND Plot layout inset): doubled it made
  the game paint a SECOND orange bar. v2.11.25: SlotThunk (container draw group
  87..97) halves it on entry / restores after, so paint sees 1x, routing 2x.
- Proven offline first: `tools/flyout-sim/emu_hittest.py` runs the REAL
  two-stage machine code (claim 0x0079AE30 → IsPointInMe 0x0099C97C);
  stock=right-36px band (the bug), both levers=full 88px (the fix).

**✅ STOCK-PARITY DOCK + NO FLASH (v2.11.30, user "Great job" 2026-07-28):**
the open-FLASH is gone (pre-scale while hidden - see
[[feedback-sc4-prescale-while-hidden]]) and the flyout now sits where STOCK puts
it. The spec came from an A-B capture against vanilla (Set-StockCompare.ps1 in
_tests\): **6 disasters visible, top arrow at the TERRAFORM (btn1) height, 4th
disaster centred on the DISASTER (btn4) button.** Old DockY 130 put the container
top at btn3 height, so item 2 - not item 4 - lined up with the tornado. At 2x the
button pitch is 120 and btn4 centre is y=860 -> btn1 centre 500, so **DockY=40**
(container top 502) and **RingDY=153** (was -27; RingDY is SCREEN px and must
rise by the same 180 the unit lifted, to hold the ring on btn4). Both live-tunable.

**JUNCTION GAP - CLOSED by LayerFix=0 (2026-07-28, user "as good as we're going
to get for now").** The gap between the ring and the bar was NOT positional - it
was the LayerFix bar-tile replay (user's own hypothesis, confirmed by a live
one-variable toggle). We skip the game's 1x ring blit and substitute a 2x
upscale of the 94x62 ring sprite, so the stock ring->bar CONNECTOR is never
painted; replaying the bar on top of the ring then exposed that seam. With
LayerFix=0 the game's native bar->ring order renders the junction as one shape.
**Do not "restore" LayerFix=1** - it was the original Circle->Strip->Pictures
z-order fix, but the junction matters more. Shipping ini: `RingDX=16 RingDY=153
DockX=-2 DockY=40 BarDX=-53 BarW=2 LayerFix=0 ClaimScale=2 SelForce=1
ClickHook=1 FlashGuard=0`.

**✅ 2026-07-31 EVENING — DISASTER FIXED FOR REAL, USER-CONFIRMED ("Disaster
works!") at v2.39.5.** The v2.39.0–.4 arc moved it to born-at-Place but the
eyes-on failed twice more before the real mechanisms surfaced: the dock gate
was a latch that could only warm while a flyout was OPEN (cold on open 1 by
construction — now warmed from the toolbar every sweep tick), and the missing
scroll arrow was a stale DECISION, not a stale frame (open-time "scroll
needed?" computed 2x window ÷ 1x pitch = "fits"; cure = born item METRICS,
not a repaint — law 21). Everything else in this memory — clicks,
ClaimScale/SelForce, junction, dock offsets — re-verified and still correct.
The v2.39.x regressions are laws 16 + 17; the arc's lessons are laws 18–22 in
[[feedback-sc4-scaling-laws]].

**v2.39.6-.8 same evening, ALL ✅ USER-CONFIRMED:** the exe re-verification
(11 funnel sites, not the 7 our comment claimed — law 22) showed every flyout
born-modern EXCEPT **Signs & Labels 0xAB954023** (opens via `sub_7E5D80`, a
byte-identical TWIN opener never hooked) — hooked v2.39.6 (FLYOPEN2),
confirmed. The disaster ARROW needed one more round: the v2.39.5 read-guard
had been refusing the born-metrics write (`metrics left to Plot` in every
DISBORN) because the offsets were in the WINDOW frame not the OBJECT frame
(+4 embed — law 21's frame corollary); v2.39.8 fixed it, confirmed "arrow
works now in both modes". **Every flyout in the game is now born-modern.**
Verified generation map: `tools\research\MECHANISM-GENERATIONS.md`; latents
documented there (unguarded city dialogs' reachable 4x, DHOOK2 f=2-only gate,
gMayorDock absent from redistributable inis, gBarCache one-sided clear).

**REMAINING:** nothing on flyouts. Hover cosmetics only if they resurface.

**KEY LEVERS/INSTRUMENTS (live in SC4UIScale.ini [Disaster], no rebuild):**
RingDX/RingDY/DockX/BarDX/BarW (layout), LayerFix, ClaimScale, SelForce (the
click fix), StripDump/ClickHook (diagnostics: DGP-OPEN/DGPKID/DCKIDS dumps
fire per flyout-open in router order w/ vtable+flags; DCLAIM; DS62/DXF).
Deploy = wait-for-close auto-deploy (game runs ELEVATED, never kill it).
Version bump per build in `src/SC4UIScaleDllDirector.cpp` (now 2.11.25).

**Offsets are DERIVED, never eyeballed:** `offset = flyoutStock − toolbarStock`
from `_vanilla-reference/FINDINGS.md` stock dims (toolbar stock (5,435)).
Hand-tuning by screenshot burned many hours and never converged.
Terraform `0x49923239` (6,−80), Terrain-FX `0xCA35CBED` (6,40) — don't re-tune.

**Other proven mechanisms banked in the Disaster work** (superseded detail in
GOD-MODE-FLYOUTS.md + HANDOFF): force-recreate-buffer (corrupt [buf+0x1c] →
Plot recreates at window size — THE lever for code-painted controls),
code-only atlas 2x upscale in BltClassThunk (read 1x art from the drawContext
buffer, nearest-upscale, magenta colorkey), permanent class-Blt patch gated by
destIsContainer (survives repaints outside Plot), bar-tile cache+replay for
z-order (LayerFix).

**COMPLETE HANDOFF BUNDLE:** `SC4TouchControls\_HANDOFF-SimCity4-Complete\`
(whole-project handoff: both DLLs + src + research MDs + regression runbook).
Live source: `src\UiSpike.cpp` (ScaleGodFlyouts + SlotThunk/SlotThunk2 +
BltClassThunk). [[reference-sc4-terraform-dock-is-the-model]]

Related: [[project-sc4-ui-scaling-northstar]], [[feedback-sc4-regression-net]],
[[reference-sc4-flyout-hittest-playbook]]
