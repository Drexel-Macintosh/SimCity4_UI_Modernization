---
name: sc4-golden-backup
description: "The user-confirmed WORKING SC4 UI-scaling config (2x, DirectX+dgVoodoo+NVIDIA, native 2400x1600) is snapshotted + restorable; where it is and the ONE gotcha"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-23T04:08:44.359Z
---

**CURRENT golden = `GOLDEN-2x-DirectX-2026-07-23\`** (same folder root;
restore with its Restore-Golden.ps1). Additive over 07-22: SC4UIScale.dll
v2.7.5-windowed (windowed render-res rule + SyncFont now manages the
install-root font automatically), SelectiveArt 215 (playlist checkbox),
DialogStatic 40/14 dialogs (incl. generic message box I-ea8cc3c6), NEW
always-on z_SC4UIScale_WebText.dat (Simtropolis.com LTEXTs). Region screen
complete across resolutions; windowed ladder live-verified. The 07-22
snapshot below is kept as the prior blessed state.

**User-confirmed working 2026-07-22 ("Good job it's fixed"). Restore from the
backup if anything breaks.**

Full snapshot (every file + every setting + restore script):
`SC4TouchControls\_working-backup\GOLDEN-2x-DirectX-2026-07-22\`
- `MANIFEST.md` — exact settings, gating state, hashes, known limitation
- `Restore-Golden.ps1` — kills game, copies all files to live locations
  (incl. the critical install-root font), relaunches
- `Documents-Plugins\` — DLLs, inis, fonts, all dats (live + gated)
- `install-Plugins\FontStyle.ini` — see gotcha below
- `install-Apps\dgVoodoo.conf`

## THE GOTCHA (corrects an earlier WRONG memory note)

**The game reads `FontStyle.ini` from `<install>\Plugins\`, NOT Documents\Plugins.**
Disassembly probe order: `<install>\Plugins\FontStyle.ini` -> `<install>\FontStyle.ini`
-> DBPF. The 2026-07-22-morning "Documents-only works" conclusion was WRONG (timing
confound); retiring the install-root font made ALL text render 1x while frames were
2x. The 2x FontStyle.ini MUST live at
`C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Plugins\FontStyle.ini`.
(The dats DO load from Documents\Plugins — only the loose FontStyle.ini is probed
by install path.) TODO: SyncFont in ScaleTier.cpp must manage the install-root
FontStyle per tier (the plugins-only-Documents change removed it — re-add).

## Config in one glance

- SC4GraphicsOptions.ini: Driver=DirectX, 2400x1600, FullScreen, ForceDrawOnScroll=true
- dgVoodoo.conf: ScalingMode=unspecified, Resolution=unforced, DDraw.dll+D3DImm.dll present
- SC4UIScale.ini: AutoScale=1, UseScaleRemap=0 (ScaleRemap OFF - active=garble), ScaleAll=1
- SC4UIScale.dll v2.7.4-renderres (AutoScale keys off ACTUAL render res: DirectX->monitor
  native, Software->requested)
- -2x package active; -15x/-3x gated

## On this panel

DirectX fullscreen is always 2x (dgVoodoo renders panel-native 2400x1600, ignores
sub-native requests). To see other factors here: SOFTWARE mode (clean, proven) or the
pending WINDOWED-DirectX path. Real target devices render at their own monitor res ->
correct factor automatically.

Related: [[sc4-resolution-control]], [[sc4-ui-scaling-northstar]], [[sc4-regression-net]].
