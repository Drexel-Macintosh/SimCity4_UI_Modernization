# Session-lifecycle hardening (v2.23.3-lifecycle)

Date: 2026-07-29. Base: deployed v2.23.2-gauges.
Goal: stale-across-city-transition state cleared in UiSpike::Disarm (PreCityShutdown).
Hard rules: only src\UiSpike.cpp, src\SC4UIScaleDllDirector.cpp, _tests\REGRESSION.md, this file.
Value-writes only in Disarm; no scaling logic / hook / list-content changes.

## Located identifiers (v2.23.2 line numbers)

- UiSpike::Disarm — UiSpike.cpp:2671 (clears armed/continuous/menuBaseline/menuBaselineCaptured only)
- lastMinimapSurfResize — function-local static, MINIMAP block, :3488 (used :3504, :3677)
- lastDataMapSurfResize — function-local static, DVMAP block, :3701 (used :3705, :3831)
- lastUdMapSurfResize — function-local static, UDMAP block, :3846 (used :3850, :3920)
- healDoneStrip / healPhase — function-local statics, ADVHEAL block, :4177-4178 (inside ScaleGodFlyouts)
- gReadyWins[16]/gReadyCount — already file-scope anon-namespace, :329-330
- gFgWaitRoot[4]/gFgWaitN[4] — already file-scope anon-namespace, :331-332
- Contradictory comment "ready set is rebuilt every sweep" — :4058-4059 (sticky NOTE at :4067 is truth);
  same falsehood also at :170 in the FLASH GUARD header comment
- Log lines to get ptr=%p: MINIMAP :3511, DVMAP :3711, UDMAP :3856
- UISCALE_VERSION_STR — SC4UIScaleDllDirector.cpp:43 ("2.23.2-gauges")
- Anon namespace opening :82 holds the globals; cIGZWin.h included :28 so cIGZWin* OK at namespace scope

## Status

- [x] Hoist 5 statics to anon namespace (after gFgWaitN, ~:334; same names, in-function usage untouched;
      each old `static` line replaced by a hoist-note comment)
- [x] Disarm clears + WHY comment block (3 map latches NULLed, gReadyCount=0, healPhase=0,
      healDoneStrip=nullptr, gFgWaitRoot[]/gFgWaitN[] zeroed; value-writes only)
- [x] ptr=%p on 3 surface-recreate log lines (arg = static_cast<void*>(pMM/pDVMap/pUdMap))
- [x] Fix "rebuilt every sweep" comments — BOTH sites: ScaleGodFlyouts bootstrap comment (primary,
      prescribed) and the FLASH GUARD header at :170 which repeated the same falsehood
- [x] Version bump 2.23.3-lifecycle (SC4UIScaleDllDirector.cpp:43)
- [x] Build Release Win32 — clean, no warnings; only 9/1101 functions recompiled (LTCG incremental)
- [x] Deploy — SimCity 4.exe ABSENT per tasklist; copied build\Release\SC4UIScale.dll ->
      Documents\SimCity 4\Plugins\SC4UIScale.dll; SHA256 match
      71D6917D396FEBC6EF4EF3E8EB9A99255FE414453FE8C2F2C802E2F132A14E9E; deployed DLL
      contains the "2.23.3-lifecycle" string
- [x] Test-DatIntegrity.ps1 — ALL PASS (11 dats + 3 font sources + 2 DLLs + frozen-bundle hash)
- [x] Test-ScaleTierDecide.ps1 — ALL PASS (14 named cases + 5000x2 random fit sweep)
- [x] REGRESSION.md — "SECOND-CITY LIFECYCLE HARDENING (v2.23.3, 2026-07-29)" section inserted
      before "## Pending" (what Disarm clears, the crash shape, ptr=%p measurability, trap signature)

## Remaining / notes for next session

- Runtime proof still owed: a city A -> region -> city B run reading the three
  "ptr=%p" log lines (does city B reuse city A's address? did the recreate re-fire?).
- gReadyWins[] entries above gReadyCount are intentionally left stale — unreadable
  (IsReadyWin iterates only to gReadyCount) and overwritten by AddReadyWin.
- VERSION-HISTORY.txt not touched (outside this task's allowed file list).
- Files changed: src\UiSpike.cpp, src\SC4UIScaleDllDirector.cpp (version only),
  _tests\REGRESSION.md, this checkpoint. Nothing else.
