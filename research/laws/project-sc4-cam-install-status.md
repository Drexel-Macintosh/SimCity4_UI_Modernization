---
name: sc4-cam-install-status
description: "SimCity 4 CAM 3.1.1 install — what's verified installed, the 3 pending user decisions (SPAM controller variant, CAP fix variant, I-R Fix download)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4a5a3d38-5382-4675-9304-a2708591f1f0
---

Steam SC4 Deluxe (1.1.641, the required digital version). Plugins split: DLLs + `a_CAM` in `C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Plugins`; NAM/SPAM/BSC etc. in `OneDrive\Documents\SimCity 4\Plugins`.

**Installed & verified (2026-07-19):** CAM Controller 3.1.1 + SIM 4.0.1 + Ordinances 3.3 (all in `a_CAM`), every DLL dependency (memo submenus/lua-sandbox/transparent-texture, SC4LuaExtensions, SC4QueryUIHooks, CustomBudgetDepartments, SC4LegalizeGamblingUpgrade, SC4ResourceLoadingHooks, SC4CustomOrdinanceHost, + `AdvancedWaterManagement.dll` which I had to pull from the SIM zip ROOT — it sits beside the readme, easy to miss). Scoty Zoning Mod extracted to Documents plugins (`z__scotyZoningMod`; the five `scoty_ZManag_*.dat` look like choose-one variants — unconfirmed, readme PDF in folder). Maxis Prop Names fix + Save Warning installed. All downloads live in `~\Downloads`.

**Pending user decisions:**
1. SPAM is installed (Documents plugins) — unsupported with the plain CAM Controller; either swap in "CAM - SPAM Controller" (Simtropolis file 36979) or shelve SPAM. User hadn't decided.
2. Universal CAP Fix: BOTH variants installed in `a_CAM\0 Universal Fixes`; readme says delete one (`._Radical` or `_Vanilla`). Recommended Vanilla.
3. I-R Fix (Simtropolis file 36841) — the ONE missing required dep; not yet downloaded (guest daily limit was hit 2026-07-19; SC4Evermore mirrors CAM files if needed).

**Why:** finishing the install without resolving 1–2 leaves an unsupported/conflicting config the CAM team won't support.

**How to apply:** resolve the three pending items before calling CAM done; CAM 3.x requires a NEW region (developed regions like the restored 2016 Fairview must stay effectively vanilla — see [[sc4-region-needs-config-bmp]] for the restore). `Plugins\Not needed` folder is still LOADED by the game (subfolders always load); left in place deliberately — its lots may be plopped in Fairview's 2016 cities.

**Fairview RESOLVED (2026-07-19):** live region = byte-verified copy of the COMPLETE backup at `OneDrive\Documents\Photo Project\High School Backups to sort\New folder\SimCity 4\Regions\Fairview` (49 cities @ 2016-09-06 save state + ORIGINAL 8x8 config.bmp + region.ini). The two `Projects\Game Backups` copies lack config.bmp (that's what caused the game to delete 40 cities at region load). My coordinate-reconstructed config.bmp came out pixel-identical to the original and survived a live game load — both approaches proven. Note: merely loading a region makes SC4 rewrite the region-view cache inside city .sc4 files (hash changes, huge byte-diff on big saves — benign, not corruption).
