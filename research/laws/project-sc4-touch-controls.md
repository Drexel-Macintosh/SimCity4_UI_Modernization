---
name: sc4-touch-controls
description: "SC4TouchControls DLL plugin — multi-touch camera control for SimCity 4 Deluxe 1.1.641 (Steam); status, key facts, deploy location; v1.0.5 release bundle is the FROZEN primary (v1.0.4 kept as history); 100% independent of the UI-scaling DLL (binary-verified)"
metadata: 
  node_type: memory
  type: project
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-07-30T04:26:29.335Z
---

Native gzcom-dll plugin adding multi-touch to SimCity 4 Deluxe 1.1.641 (Steam, dev PC). One finger = mouse (stock promotion); two-finger drag = closed-loop anchor pan (PickTerrain + SetScrolling); pinch = ZoomIn/ZoomOut step; twist ±25° = RotateLeft/Right; second-finger-mid-drag sends ESC (gated by GetCurrentViewInputControl()->AmCapturing() so it can't eat dialogs) + balancing WM_LBUTTONUP.

- Source: `Surface 1 Project\1 Completed Projects\SC4TouchControls\` (moved from a Development 2026-07-19; src + vendored gzcom-dll pinned 08c529bc + README + dist\SC4TouchControls-v1.0.4 release bundle). Built VS 2026 MSBuild, v145, Win32/x86, WindowsTargetPlatformVersion 10.0.26100.0.
- **DLL plugins DO load from `Documents\SimCity 4\Plugins`** (proven empirically 2026-07-19; user prefers that folder — deploy DLL+INI+log there, NOT the install dir, despite community docs saying install-dir only).
- Logger must use `_wfsopen(_SH_DENYWR)` (share-readable while game runs); read it with FileStream FileShare::ReadWrite (Get-Content fails on it).
- Engine survives event gaps: still fingers produce no WM_POINTER events (and [[pixelsensetouch-bridge]] skips identical frames), so SinglePassthrough never stale-resets and Idle re-enters gestures on ≥2-contact frames.
- Same DLL is expected to work on the Surface 1.0 table via PS2T pointer injection AND any touchscreen laptop (WM_POINTER is WM_POINTER) — table validation still pending.
- **🔒 FROZEN RELEASE (updated 2026-07-30, user-ordered): the PRIMARY frozen bundle is now `dist\SC4TouchControls-v1.0.5\`** — the deployed touch-ONLY build from the 2026-07-21 DLL split (identical v1.0.4 gestures; 208,896 bytes; read-only + FROZEN-MANIFEST.txt SHA256s). `dist\SC4TouchControls-v1.0.4\` (pre-split binary) is preserved unchanged as history. Test-DatIntegrity asserts BOTH bundle hashes AND that deployed Plugins\SC4TouchControls.dll == frozen v1.0.5. **100% INDEPENDENCE is verified, not just claimed (2026-07-30): SC4TouchControls.vcxproj compiles ONLY touch modules + Logger/Settings/VersionDetection + gzcom base (no CodePatches/UiSpike/ScaleRemap — the old DLL-REFERENCE "present in both builds" line was WRONG and is corrected), and the shipped binary string-scans clean of every scaling marker.** NEVER modify either dist folder from the UI-scaling (v2.x) work. Recovery: installing the v1.0.5 folder's DLL+ini alone restores shipped touch exactly (its ini is the CLEAN touch-only one; the live Plugins ini's stale [Scaling]/[UiSpike] sections are ignored dead text). Touch source modules must not be edited during UI-scaling work.
- Status 2026-07-19: **v1.0.4 SHIPPED — all four gestures user-confirmed perfect.** Pan = the game's native right-drag driven with the REAL cursor+button (SetCursorPos+SendInput, foreground-guarded, guaranteed release) — SC4 POLLS the physical cursor during pan and ignores PostMessage'd mouse input (proven; don't retry message-based pan). Gesture intent classifier: common-vs-differential finger motion, differential split radial (pinch) vs arc (twist) — absolute centroid travel misclassifies pivot twists as pans. v1.0.2+ fixed stale-scroll-velocity (correct every update; stationary fingers dead-stop).
- Machine facts: dev box HAS full Windows SDKs (22621/26100+WDK/28000) under `C:\Program Files (x86)\Windows Kits\10` — the Glob tool falsely reported them absent (sandbox quirk on that tree; trust PowerShell listings). SC4 is single-instance; its process resists taskkill from this session (Access denied) — ask the user to close the window instead.
