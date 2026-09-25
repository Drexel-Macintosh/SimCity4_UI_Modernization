# PackageFiles.psd1 - THE list of files a working install holds (audit B12,
# 2026-09-25). Two scripts copy from it and nothing else lists these files:
#   _tests\Deploy-OnGameClose.ps1   copies every row into the live Plugins tree
#   _packaging\Build-Dist.ps1       copies every row except DeployOnly into the
#                                   release bundle
# Both then call _tests\Convert-ToPayloadLayout.ps1, which turns the
# tier-tagged names below into the payload layout. _tests\Test-DatIntegrity.ps1
# derives its deployed == built pairs and font sources from these rows too.
#
# WHY A DATA FILE. Until B12, Build-Dist regex-parsed Deploy's Copy-Item lines.
# 30 of those lines were invisible to the regex (named-parameter form,
# expression-built paths) and Build-Dist re-listed them by hand; SelectorUI,
# CsiIcons and the ZCarbon set each went missing from bundles through that gap
# before a hard assert caught it. A package is now one row here, and both
# scripts see the same rows.
#
# A PACKAGE IS NOT FINISHED UNTIL IT IS HERE AND IN _tests\Test-DatIntegrity.ps1.
# Packages have rotted from exactly that omission (#58 ThirdPartyUI, #116
# ItemIcons/ItemIconsSub, NamIcons) while every gate stayed green.
#
# Each row:
#   Src   source path, relative to the repo root
#   Dir   destination folder: 'plug' (Plugins root; only the DLL - the game's
#         DLL loader is top-level only), 'our' (Plugins\010-SC4UIScale) or
#         'zzz' (Plugins\zzz-SC4UIScale, which sorts after every mod folder)
#   Name  destination file name. 2x is the plain or -2x name; 1.5x and 3x ship
#         as .x1-disabled, and the DLL arms the tier it resolves at boot.
# Optional flags:
#   Optional   = $true  a missing source is a valid state; skip the row
#   Carbon     = $true  Deploy copies it only when the Carbon Skin builds exist
#                       on this machine; Build-Dist always requires it
#   Selector   = $true  Deploy's SelectorUI block decides armed or stashed
#   DeployOnly = $true  never in the release bundle
#   Live       = $true  the DLL rewrites this file at boot, so its deployed bytes
#                       are not a build output (Test-DatIntegrity skips its hash)
#
# NOT LISTED: z_SC4UIScale_MenuFix.dat. It rewrites CAM's gameplay submenu data
# rather than scaling any UI, so shipping it is a decision about a third-party
# mod's content. Build-Dist -IncludeUnbuildable can pull it from a live install.
@{
    Files = @(
        @{ Src = 'build\Release\SC4UIScale.dll'; Dir = 'plug'; Name = 'SC4UIScale.dll' }

        # SelectiveArt (v4.0.3, STABLE-FILENAME PILOT): all three tier sources ship
        # PERMANENTLY suffixed - none of them is "the active one" by filename any
        # more. The DLL's SyncDatStable copies the right tier's bytes onto the one
        # stable name below at boot, so sc4pac (or a manual deploy re-run) always
        # finds z_SC4UIScale_SelectiveArt.dat under the SAME name regardless of tier.
        @{ Src = 'tools\selective-safe\z_SC4UIScale_SelectiveArt.dat';    Dir = 'our'; Name = 'z_SC4UIScale_SelectiveArt-2x.dat.x1-disabled' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_SelectiveArt-15x.dat';  Dir = 'our'; Name = 'z_SC4UIScale_SelectiveArt-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_SelectiveArt-3x.dat';    Dir = 'our'; Name = 'z_SC4UIScale_SelectiveArt-3x.dat.x1-disabled' }
        # The STABLE file itself: ships as the 2x content by default (today's
        # out-of-the-box tier), and SyncDatStable rewrites it to match whatever the
        # player's own AutoScale/selector choice resolves to on next boot. Live:
        # the DLL rewrites it, so Test-DatIntegrity does not hash it against a build.
        @{ Src = 'tools\selective-safe\z_SC4UIScale_SelectiveArt.dat';    Dir = 'our'; Name = 'z_SC4UIScale_SelectiveArt.dat'; Live = $true }

        @{ Src = 'tools\dialog-static\z_SC4UIScale_DialogStatic.dat';     Dir = 'our'; Name = 'z_SC4UIScale_DialogStatic-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_DialogStatic-15x.dat';  Dir = 'our'; Name = 'z_SC4UIScale_DialogStatic-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_DialogStatic-3x.dat';    Dir = 'our'; Name = 'z_SC4UIScale_DialogStatic-3x.dat.x1-disabled' }

        # ITEM ICONS - ADDED 2026-08-03 (#116). These were MISSING from the deploy
        # manifest for its whole life, and ScaleTier actively tier-manages them
        # (ScaleTier.cpp: the SyncDat "z_SC4UIScale_ItemIcons" site), so the deployed
        # copies had frozen at whatever build epoch last hand-placed them.
        # SOURCE IS THE **UNTAGGED** FILE. tools\itemicons\ holds BOTH
        # z_SC4UIScale_ItemIcons.dat and z_SC4UIScale_ItemIcons-2x.dat, and they are
        # not the same build. Test-DatIntegrity treats the UNTAGGED one as canonical
        # (it is what SelectiveArt/DialogStatic do too - the 2x tier's source carries
        # no tag). Deploying from the tagged copy makes DatIntegrity FAIL, which is
        # how this was caught rather than shipped.
        @{ Src = 'tools\itemicons\z_SC4UIScale_ItemIcons.dat';            Dir = 'our'; Name = 'z_SC4UIScale_ItemIcons-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ItemIcons-15x.dat';     Dir = 'our'; Name = 'z_SC4UIScale_ItemIcons-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ItemIcons-3x.dat';       Dir = 'our'; Name = 'z_SC4UIScale_ItemIcons-3x.dat.x1-disabled' }

        # ItemIconsSub - ADDED 2026-08-03 (#116), same omission as ItemIcons above.
        # ScaleTier.cpp's SyncDat site tier-manages this one too.
        @{ Src = 'tools\itemicons\_work\z_SC4UIScale_ItemIconsSub-2x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_ItemIconsSub-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ItemIconsSub-15x.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_ItemIconsSub-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ItemIconsSub-3x.dat';     Dir = 'zzz'; Name = 'z_SC4UIScale_ItemIconsSub-3x.dat.x1-disabled' }

        # CsiIcons - ADDED 2026-08-18 (#188). The U-Drive-It offer balloon icons
        # (City Situation Indicators). Tier suffixes follow the ItemIconsSub
        # pattern: the ACTIVE tier keeps its plain .dat name, the other two ship
        # .x1-disabled and ScaleTier renames. These rows once shipped INVERTED
        # (2026-08-18 -> 2026-08-19: 15x at the plain name, so a 2x install got
        # 1.5x icons); every gate asked only "is the package present?".
        @{ Src = 'tools\packages\2x\z_SC4UIScale_CsiIcons-2x.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_CsiIcons-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_CsiIcons-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_CsiIcons-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_CsiIcons-3x.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_CsiIcons-3x.dat.x1-disabled' }

        # UncoveredIcons - ADDED 2026-08-15 (#149). ItemIcons a third-party LOT ships
        # that no package of ours covered. Rebuild with:
        #     python tools\itemicons\build_uncovered_icons.py
        # which rediscovers the set from the player's OWN Plugins tree - so it is
        # OPTIONAL (absent on a clean install; a hard copy here was a RELEASE BUG)
        # and DEPLOY-ONLY (a shipped copy would be someone else's).
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_UncoveredIcons-2x.dat';  Dir = 'zzz'; Name = 'z_SC4UIScale_UncoveredIcons-2x.dat';               Optional = $true; DeployOnly = $true }
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_UncoveredIcons-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_UncoveredIcons-15x.dat.x1-disabled'; Optional = $true; DeployOnly = $true }
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_UncoveredIcons-3x.dat';  Dir = 'zzz'; Name = 'z_SC4UIScale_UncoveredIcons-3x.dat.x1-disabled';  Optional = $true; DeployOnly = $true }

        # SelectorUI-1x - ADDED 2026-08-19. The in-game scale selector at the STOCK
        # tier, and the ONLY package whose gate is the ABSENCE of a tier. Without it
        # the stock tier is a one-way door out of the mod. Rebuild with:
        #     python tools\dialog-static\build_selector_1x.py
        # Deploy arms or stashes it from the armed-tier snapshot (see its block);
        # the bundle ships it at this name and the payload converter seeds it.
        @{ Src = 'tools\packages\1x\z_SC4UIScale_SelectorUI-1x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_SelectorUI-1x.dat'; Selector = $true }

        # WebText (user decision 2026-08-05: ship it - it makes the visible text
        # match the WebRedirect the DLL already performs at every tier). Built by
        # tools\webtext\build_webtext.py.
        @{ Src = 'tools\webtext\z_SC4UIScale_WebText.dat'; Dir = 'our'; Name = 'z_SC4UIScale_WebText.dat' }

        # CAM GRAPH LABELS (#147, 2026-08-06). ONE 20-byte LTEXT, TIER-INDEPENDENT:
        # the caption for label 0xFF5D2E9F, which CAM's Power and Water charts bind
        # and no installed archive carries. We supply the missing resource; we never
        # touch CAM's file. Built by tools\itemicons\build_cam_graph_labels.py.
        # Reported upstream (tools\research\UPSTREAM-CAM-REPORT.md #4); DELETE THIS
        # ROW and the dat if CAM ever fixes the id. Inert without CAM.
        @{ Src = 'tools\packages\shared\z_SC4UIScale_CamGraphLabels.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_CamGraphLabels.dat' }

        # SaveWarningUI (v2.38.0, task #79c): 2x copies of the two in-city quit/exit
        # confirm scripts built from the save-warning MOD's versions. MUST land in
        # zzz-SC4UIScale - root Plugins files load BEFORE subfolders, so a root copy
        # could never beat the mod in 150-mods\ (the load-order law). ScaleTier
        # gates it on that mod still being installed.
        @{ Src = 'tools\dialog-static\z_SC4UIScale_SaveWarningUI.dat';    Dir = 'zzz'; Name = 'z_SC4UIScale_SaveWarningUI-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_SaveWarningUI-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_SaveWarningUI-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_SaveWarningUI-3x.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_SaveWarningUI-3x.dat.x1-disabled' }

        # CamUI (v2.38.3): the SIX dialog-static targets CAM replaces, built from
        # CAM's own scripts; + v2.97.0 (#154) CAM's city info screen, its civic and
        # school query panels and the nine bitmaps the info screen draws. Same zzz-
        # rule and dependency gate.
        @{ Src = 'tools\dialog-static\z_SC4UIScale_CamUI.dat';    Dir = 'zzz'; Name = 'z_SC4UIScale_CamUI-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_CamUI-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_CamUI-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_CamUI-3x.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_CamUI-3x.dat.x1-disabled' }

        # ThirdPartyUI (task #58 root cause, found 2026-08-02): this package was
        # NEVER in the deploy list, so the deployed copy froze at the 2026-07-29
        # build epoch and kept referencing clone TGIs that stopped shipping. Byte
        # sizes of stale and fresh dats are IDENTICAL (the rewrite swaps
        # equal-length hex), so only content/hash comparison catches this class.
        @{ Src = 'tools\selective-safe\z_SC4UIScale_ThirdPartyUI.dat';    Dir = 'zzz'; Name = 'z_SC4UIScale_ThirdPartyUI-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ThirdPartyUI-15x.dat';  Dir = 'zzz'; Name = 'z_SC4UIScale_ThirdPartyUI-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ThirdPartyUI-3x.dat';    Dir = 'zzz'; Name = 'z_SC4UIScale_ThirdPartyUI-3x.dat.x1-disabled' }

        # WarriorUI (task #94, 2026-08-02): 2x copies of warrior's god-terraforming-
        # in-mayor-mode scripts + ITS art. Same zzz- rule and dependency gate.
        @{ Src = 'tools\selective-safe\z_SC4UIScale_WarriorUI.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_WarriorUI-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_WarriorUI-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_WarriorUI-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_WarriorUI-3x.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_WarriorUI-3x.dat.x1-disabled' }

        # RaiseUI (2026-08-30): warrior's "Raise the UI Mod" ships only SCRIPTS, no
        # art, so the game runs its 1x `imagerect` source rects against OUR 2x art
        # sheets. Our copies carry the MOD'S scripts with imagerect scaled and
        # `area=` untouched, so the raise survives. Same zzz- rule and gate.
        @{ Src = 'tools\selective-safe\z_SC4UIScale_RaiseUI.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_RaiseUI-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_RaiseUI-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_RaiseUI-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_RaiseUI-3x.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_RaiseUI-3x.dat.x1-disabled' }

        # ZCarbonRaiseUI (2026-08-30): Scoty's OPTIONAL composed Carbon+Raise
        # scripts, for the one combination neither RaiseUI nor ZCarbonArt can serve.
        # Sorts after ZCarbonArt so it wins both contested scripts when its gate is
        # open, and is gated on the composed file itself. NOT Carbon-flagged: Deploy
        # has always copied it unconditionally.
        @{ Src = 'tools\selective-safe\z_SC4UIScale_ZCarbonRaiseUI.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonRaiseUI-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ZCarbonRaiseUI-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonRaiseUI-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ZCarbonRaiseUI-3x.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonRaiseUI-3x.dat.x1-disabled' }

        # ZCarbonPauseOff (2026-08-30): a fully transparent sheet over the carbon
        # gold pause border, sorting after ZCarbonArt and armed ONLY when a pause
        # remover is installed. Built by tools\itemicons\build_carbonpauseoff.py.
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_ZCarbonPauseOff-2x.dat';  Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonPauseOff-2x.dat' }
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_ZCarbonPauseOff-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonPauseOff-15x.dat.x1-disabled' }
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_ZCarbonPauseOff-3x.dat';  Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonPauseOff-3x.dat.x1-disabled' }

        # RegionCensusUI (2026-08-30): null-45's mod-ONLY region census dialog,
        # which never scales itself while our 2x fonts scale its text. Built by
        # dialog-static (a static, never-swept window, so its area= is ours).
        @{ Src = 'tools\dialog-static\z_SC4UIScale_RegionCensusUI.dat';    Dir = 'zzz'; Name = 'z_SC4UIScale_RegionCensusUI-2x.dat' }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_RegionCensusUI-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_RegionCensusUI-15x.dat.x1-disabled' }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_RegionCensusUI-3x.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_RegionCensusUI-3x.dat.x1-disabled' }

        # NamIcons (task #139, 2026-08-05): 1.5x/2x/3x copies of the Network Addon
        # Mod's OWN 392 menu ItemIcons, gated in ScaleTier on the presence of
        # NetworkAddonMod_Controller.dat. NAM lives in 770-network-addon-mod\ and
        # only zzz- sorts after it. These were hand-placed the session they were
        # built and caught missing from the manifest by Build-Dist the same day.
        # Generator: tools\itemicons\rebuild_namicons.py (all three tiers land in
        # tools\itemicons\out\).
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_NamIcons-2x.dat';  Dir = 'zzz'; Name = 'z_SC4UIScale_NamIcons-2x.dat' }
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_NamIcons-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_NamIcons-15x.dat.x1-disabled' }
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_NamIcons-3x.dat';  Dir = 'zzz'; Name = 'z_SC4UIScale_NamIcons-3x.dat.x1-disabled' }

        # WebButtonUI (2026-08-21): copies of the cyclone-boom Web Button
        # Improvement Mod's web-button bitmap {856DDBAC,46A006B0,14416302}, gated
        # in ScaleTier on the mod's presence. Generator:
        # tools\itemicons\rebuild_webbutton.py.
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_WebButtonUI-2x.dat';  Dir = 'zzz'; Name = 'z_SC4UIScale_WebButtonUI-2x.dat' }
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_WebButtonUI-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_WebButtonUI-15x.dat.x1-disabled' }
        @{ Src = 'tools\itemicons\out\z_SC4UIScale_WebButtonUI-3x.dat';  Dir = 'zzz'; Name = 'z_SC4UIScale_WebButtonUI-3x.dat.x1-disabled' }

        # ---- ZCarbon* (v4.3.0, 2026-08-25): Scoty Carbon Skin adaptations -------
        # Carbon-sourced scaled twins of every TGI the skin and our packages both
        # cover; gated in ScaleTier on the skin's dats at exact sizes. Z-late base
        # names are LOAD-BEARING (must sort after every sibling in zzz- to win
        # shared TGIs; REGRESSION.md 2026-08-25 "zzz-INTERNAL SORT TRAP").
        # THEY SHIP (v4.3.1), exactly like CamUI / NamIcons / WarriorUI /
        # ThirdPartyUI / SaveWarningUI / WebButtonUI: a mod's own artwork and
        # layouts, enlarged to the player's factor, gated on that mod being
        # installed. Attribution is in THIRD-PARTY-NOTICES.md; the packages are
        # inert without the skin because every one carries a kThirdPartyDeps row.
        # Carbon = $true: on a machine without the carbon builds (fresh clone, no
        # skin) these sources do not exist, so Deploy skips them rather than abort
        # mid-way; Build-Dist refuses to build a bundle without them.
        @{ Src = 'tools\dialog-static\z_SC4UIScale_ZCarbonUI.dat';            Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonUI-2x.dat';                      Carbon = $true }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ZCarbonUI-15x.dat';         Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonUI-15x.dat.x1-disabled';         Carbon = $true }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ZCarbonUI-3x.dat';           Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonUI-3x.dat.x1-disabled';          Carbon = $true }
        @{ Src = 'tools\dialog-static\z_SC4UIScale_ZCarbonCamUI.dat';         Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonCamUI-2x.dat';                   Carbon = $true }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ZCarbonCamUI-15x.dat';      Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonCamUI-15x.dat.x1-disabled';      Carbon = $true }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ZCarbonCamUI-3x.dat';        Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonCamUI-3x.dat.x1-disabled';       Carbon = $true }
        @{ Src = 'tools\dialog-static\z_SC4UIScale_ZCarbonSaveWarning.dat';   Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonSaveWarning-2x.dat';             Carbon = $true }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ZCarbonSaveWarning-15x.dat'; Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonSaveWarning-15x.dat.x1-disabled'; Carbon = $true }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ZCarbonSaveWarning-3x.dat';  Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonSaveWarning-3x.dat.x1-disabled'; Carbon = $true }
        @{ Src = 'tools\selective-safe\z_SC4UIScale_ZCarbonArt.dat';          Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonArt-2x.dat';                     Carbon = $true }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ZCarbonArt-15x.dat';        Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonArt-15x.dat.x1-disabled';        Carbon = $true }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ZCarbonArt-3x.dat';          Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonArt-3x.dat.x1-disabled';         Carbon = $true }
        @{ Src = 'tools\selective-safe\z_SC4UIScale_ZCarbonStyles.dat';       Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonStyles-2x.dat';                  Carbon = $true }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ZCarbonStyles-15x.dat';     Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonStyles-15x.dat.x1-disabled';     Carbon = $true }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ZCarbonStyles-3x.dat';       Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonStyles-3x.dat.x1-disabled';      Carbon = $true }
        @{ Src = 'tools\selective-safe\z_SC4UIScale_ZCarbonNam.dat';          Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonNam-2x.dat';                     Carbon = $true }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ZCarbonNam-15x.dat';        Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonNam-15x.dat.x1-disabled';        Carbon = $true }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ZCarbonNam-3x.dat';          Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonNam-3x.dat.x1-disabled';         Carbon = $true }
        @{ Src = 'tools\selective-safe\z_SC4UIScale_ZCarbonGodMod.dat';       Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonGodMod-2x.dat';                  Carbon = $true }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ZCarbonGodMod-15x.dat';     Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonGodMod-15x.dat.x1-disabled';     Carbon = $true }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ZCarbonGodMod-3x.dat';       Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonGodMod-3x.dat.x1-disabled';      Carbon = $true }
        @{ Src = 'tools\research\carbon\z_SC4UIScale_ZCarbonIcons.dat';       Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonIcons-2x.dat';                   Carbon = $true }
        @{ Src = 'tools\packages\15x\z_SC4UIScale_ZCarbonIcons-15x.dat';      Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonIcons-15x.dat.x1-disabled';      Carbon = $true }
        @{ Src = 'tools\packages\3x\z_SC4UIScale_ZCarbonIcons-3x.dat';        Dir = 'zzz'; Name = 'z_SC4UIScale_ZCarbonIcons-3x.dat.x1-disabled';       Carbon = $true }

        # FONT TIER SOURCES (#57 phase 4, 2026-08-02). The DLL's ScaleTier::SyncFont
        # copies the active tier's file over FontStyle.ini at boot, so ONLY these
        # three sources belong here; never list FontStyle.ini itself (#182: an
        # empty live-named FontStyle.ini crashed a vanilla game). The 2x source is
        # tools\fonts\FontStyle.candidate.ini - there is no tools\packages\2x\ font;
        # it is byte-identical to make_fontstyle.py's factor-2 output apart from its
        # hand-written ";;" banner (asserted by --selfcheck).
        @{ Src = 'tools\fonts\FontStyle.candidate.ini';  Dir = 'our'; Name = 'FontStyle-2x.ini' }
        @{ Src = 'tools\packages\15x\FontStyle-15x.ini'; Dir = 'our'; Name = 'FontStyle-15x.ini' }
        @{ Src = 'tools\packages\3x\FontStyle-3x.ini';   Dir = 'our'; Name = 'FontStyle-3x.ini' }
    )
}
