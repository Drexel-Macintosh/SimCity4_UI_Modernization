---
name: sc4-resolution-control
description: "EXACT mechanism for controlling SC4 resolution + renderer (the thing that caused a long thrash): SC4GraphicsOptions.ini + software mode, NO dgVoodoo needed for stock modes"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-22T07:34:02.428Z
---

**How SC4's resolution + renderer are controlled on this machine. Read before ANY
resolution/display change — this is the thing that got overcomplicated on 2026-07-22.**

## The ONE knob: SC4GraphicsOptions.ini

`<HOME>\OneDrive\Documents\SimCity 4\Plugins\SC4GraphicsOptions.ini`
is read by the community mod **SC4GraphicsOptions.dll** (NOT our code). It forces:
```
Driver=Software        <- or DirectX. Software = CPU render, no GPU, no dgVoodoo, no 2048 cap.
WindowWidth=1024       <- stock modes: 800/600, 1024/768, 1280/1024, 1600/1200
WindowHeight=768
WindowMode=FullScreen
ForceDrawOnScroll=true  <- keep true (fixes partial-redraw garble)
```
Change resolution = edit WindowWidth/Height here + relaunch. That's it.

## ⚠️ FontStyle.ini LIVES IN `<install>\Plugins\` (corrects an earlier wrong note)

The game probes `FontStyle.ini` at `<install>\Plugins\FontStyle.ini` ->
`<install>\FontStyle.ini` -> DBPF (disassembly). NOT Documents\Plugins (the
2026-07-22-morning "Documents-only" test had a timing confound and was WRONG).
Retiring the install-root copy makes ALL text render 1x while frames are 2x.
The 2x font MUST be at
`C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Plugins\FontStyle.ini`.
The DATS still load fine from Documents\Plugins; only the loose FontStyle.ini
is probed by install path. See [[sc4-golden-backup]].

## THE SIMPLE, CORRECT SETUP (proven clean, user "good job")

Software renderer + stock resolution + dgVoodoo removed = SC4 renders stock
PERFECTLY, no GPU/wrapper/DPI complexity.
1. `Driver=Software` in SC4GraphicsOptions.ini
2. a stock WindowWidth/Height (<=1600x1200)
3. dgVoodoo aside: rename `<install>\Apps\DDraw.dll` and `D3DImm.dll` -> `.off`
   (install = C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe)
4. our UI scaler layers on top (SC4UIScale.dll); at stock res the AutoScale
   tier auto-inerts unless a package fits.
Proof capture: tools\capture\out\software-1024.png (clean 1024x768 stock).

## ⚠️ CRITICAL: DirectX renders at the MONITOR's native mode, NOT the requested res

Proven 2026-07-22 (v2.7.4): with Driver=DirectX + dgVoodoo on the 2400x1600
panel, requesting WindowWidth/Height=1600x1200 does NOT make the game render
1600x1200 — dgVoodoo renders at the MONITOR native (2400x1600) and reports THAT
to the game (the cIGZWin tree is 2400x1600). Only SOFTWARE mode renders at the
requested size. This is why every "1600x1200 in production" test on this panel
was really a 2400x1600 render, and why AutoScale (which read the ini 1600x1200
and picked 1.5x) mismatched the actual 2x render -> the "giant blurry UI" garble.

**THE FIX (SC4UIScaleDllDirector ctor, v2.7.4-renderres):** AutoScale keys off
the ACTUAL RENDER resolution: `Driver=DirectX -> render = GetSystemMetrics
monitor size; Driver=Software -> render = requested WindowWidth/Height`. Set
PMv2 DPI-awareness BEFORE reading the monitor (physical px). So on THIS panel,
production DirectX always -> tier 2.0 (the validated golden state); a genuine
1600x1200 DISPLAY (monitor=1600x1200) -> tier 1.5. Correct on any device.

**ScaleRemap is OFF by default** (ini [Scaling] UseScaleRemap=0, code default
false). Its internal!=present metric lies are the rejected whole-frame approach
and were the OTHER half of the garble - they double-transform against dgVoodoo's
present-scaling. Never re-enable to fix resolutions.

## dgVoodoo = ONLY for big-display DirectX play

dgVoodoo (DDraw.dll + D3DImm.dll in Apps\, config dgVoodoo.conf) exists ONLY
because `Driver=DirectX` at >2048 wide (this 2400x1600 panel) needs a wrapper +
the NVIDIA card. It is NOT needed for correctness or for testing scaling.
DO NOT route stock/sub-native resolutions through dgVoodoo — that was the entire
"garble" saga. Restore dgVoodoo only when deliberately doing DirectX big-display.
When restored: dgVoodoo.conf ScalingMode=unspecified is the known-good.

## Hard rules (user directives)

- NEVER touch/disable SC4TouchControls.dll for resolution work - separate + shipped.
- ScaleRemap (in SC4UIScale) is the rejected whole-frame approach; do NOT use it to
  fix resolutions. (It stays in the DLL because its AttachWindow window-cover is
  load-bearing for the 2400x1600 DirectX window ONLY; irrelevant in software mode.)
- Restore procedure after experiments: dgVoodoo DLLs back, ScalingMode=unspecified,
  all our Plugins files present, SC4UIScale.ini Enabled=1, native 2400x1600 -> boot,
  expect "tier 2.00" + "9/9 region panels" in SC4UIScale.log.

Related: [[sc4-ui-scaling-northstar]] (has the ARCHITECTURE CORRECTION note),
[[sc4-regression-net]], [[sc4-touch-controls]].
