---
name: reference-sc4-csi-indicator
description: "SC4 City Situation Indicator (the U-Drive-It offer balloon) — TWO quads, both sized by INLINE .text immediates; the icon's size is also its click box."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-18T11:57:58.294Z
---

**#188 CLOSED 2026-08-18, user-confirmed at 3x/3840x2160** (v3.0.38).

The blue offer balloon above a U-Drive-It vehicle is a **City Situation
Indicator**, category 4 of the dispatch-indicator system. Full write-up:
`SC4UIScale\tools\research\CITY-SITUATION-INDICATORS.md`.

**It is the only in-world overlay in SC4 that the player clicks.**

Drawer `cSC4DispatchVehicleView::Draw` = **0x0046D990** (identified by
suppression, user-confirmed "THEY'RE GONE"). Geometry built in **0x0046C8B0**,
called from `AddIndicator` 0x0046F240 at 0x0046F616.

**TWO quads, and this is the whole trap** — every single-number fix produced a
half-result for a day:

* **pin / backing**, 64x64 — eight ±32.0f immediates at 0x0046EABD, 0x0046EACA,
  0x0046EAF6, 0x0046EB01, 0x0046EB2D, 0x0046EB38, 0x0046EB64, 0x0046EB6F
  (`C7 84 24 …`, imm at instruction+7)
* **icon + CLICK BOX**, 35x35 — `mov eax,0x420C0000` at 0x0046CC47, imm at
  **0x0046CC48**, inside the CSI-only branch `cmp [esi+4],4`. Stored to the
  record's width AND height (+0xD0/+0xD4); Draw halves them to ±17.5.

⛔ **0x0046CCB9 is the same instruction with 32.0f on the NON-CSI branch —
never patch it.**

**Both levers are INLINE IMMEDIATES IN `.text`.** That is why months of
`.rdata` constant sweeps were honest nulls — see law 99 in
[[feedback-sc4-scaling-laws]]. `0x00A8819C = 42.0f` is NOT a size: it feeds the
quad's TRANSLATION, so it was live and silent the whole time (law 103).

Art: eight PNG strips (`type 0x856DDBAC`), 152x38 = four 38x38 states,
instances 0x4BB1305D car / 0x4BB1305E heli / 0x4BB1305F police / 0x4BB13060
ferry / 0x0C0305C3 sail / 0x0C0305C4 plane / 0x0C0305C5 tank / 0x0C0305C6
train. **Each exists TWICE, pixel-identical, in groups 0x46A006B0 (the drawn
one) and 0x1ABE787D** — a tracer covering only one group wrongly exonerated
the art for a full day. The eight are provably complete: all four automata LUA
resources were QFS-decompressed and every `csi_image` extracted, 8 of 8
covered.

Shipped in `ApplyCsiIndicatorScale` (`src/CodePatches.cpp`), both-or-neither,
tier-general. Art at `tools/packages/{15x,2x,3x}/z_SC4UIScale_CsiIcons-*.dat`.

⚠ STILL OWED: the eight pin immediates are NOT category-guarded, so other
dispatch-indicator categories reach that quad. No emergency marker was on
screen during either eyes-on — untested blast radius, not a cleared one.
