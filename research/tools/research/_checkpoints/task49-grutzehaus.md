# Task #49 — duplicated menu icon (Grutzehaus) — working checkpoint

Session 2026-07-29. Deployed at start: v2.23.1-textsweep.
Raw notes, appended as measured. Final answer at the bottom.

## SYMPTOM
Grutzehaus landmark button (mayor-mode landmarks menu) shows TWO SMALL icons
side by side instead of one icon filling the doubled 88px cell.

---

## STEP 1 — which group/TGI does the submenus DLL actually read? (ANSWERED)

Mod located: `memo.submenus.dll` 2.1.0 (Plugins root) + its dats under
`<Plugins>\150-mods\memo.submenus-dll.2.1.0.sc4pac\submenus\`.
**Full source available at tag 2.1.0** in
`tools\research\submenus-dll-src\` — no byte-scan needed, read the source.

`src\SubmenusDllDirector.cpp:404-413`:
```cpp
uint32_t replaceIconIfMissing(uint32_t itemIconId) {
    auto key = cGZPersistResourceKey(0x856ddbac, 0x6a386d26, itemIconId);
    if (!pResMan->TestForKey(key)) {
        return 0x144161ec;   // missing thumb icon IID
    }
    return itemIconId;
}
```
Called from `Hook_AddBuildingsToItemList2`, injected at **0x7f036a**
(`AddBuildingsToItemList2_InjectPoint`), which writes the chosen instance to
`[esp+0xc4+0xc]` (the +0xc compensates its own 3 pushes).

**Group is 0x6A386D26 — verified by disassembling the real consumer**, not inferred:
```
0x7F0358  push 0x8a2602b8            ; Item Icon prop
0x7F035E  call 0x5fd480              ; GetProperty
0x7F036A  mov [esp+0xc4], ecx        ; <-- MOD INJECT POINT (instance slot)
0x7F037C  push edx                   ; (esp shifts -4 from here)
0x7F037D  mov [esp+0xc0], 0x856ddbac ; TYPE   at E+0xbc
0x7F0388  mov [esp+0xc4], 0x6a386d26 ; GROUP  at E+0xc0   <-- 0x6A386D26
0x7F0393..0x7F039A                   ; image load
```
TGI struct = {type E+0xbc, group E+0xc0, instance E+0xc4}; the instance the mod
writes survives. Group also confirmed 0x6a386d26 at site 2 (0x7ECB4C) including
its alternate-icon branch (0x7ECB12 `push 0xabe1af70` when `[edx+0x4c]` is true,
pre-seeded with 0x144161ec at 0x7ECAFE) and at site 1 (0x78EE11).

=> **The group we override (0x6A386D26) is CORRECT at all three sites.**
The "wrong group" hypothesis (0x46A006B0 / own group) is DEAD.
Note: `0x856DDBAC/0x46A006B0/0xAC581B70..74` also appears in the mod
(`initializeMenuFrames`) but that is the submenu-essentials MENU FRAME art,
not the item-icon path.

## STEP 2 — geometry of the missing-thumb strip (CORRECT, so not the cause)
- stock 1x `{856DDBAC, 6A386D26, 144161EC}` (SimCity_1.dat) = **176x44** (4 x 44px states)
- our 2x in `zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat` = **352x88** (4 x 88px states)
- exactly 2x in BOTH axes, same 4-state count. Load-order scan: ours is the
  ONLY copy in the Plugins tree and it WINS (zzz- sorts last).
- Full-set check: **0 of 391** shipped 2x icons mismatch 2x-of-source.

=> geometry is not the bug either.

## STEP 3 — THE ACTUAL ROOT CAUSE (measured)

The premise handed to me ("0xED2174A0 has NO icon art in any installed dat, so it
falls back to Missing Thumb 0x144161EC") is **FALSE**.

Grutzehaus's exemplar (verified by my own both-format parser — the shipped
`parse_exemplars.py` is binary-only):
```
[BIN] T-6534284a_G-ad1d67dc_I-ed2174a0  name='Grutzehaus_DLC'  ItemIcon=0xED2174A0
```
(24 of the 30 CAM_DLC_Landmark_Building exemplars are TEXT format; Grutzehaus
itself is BINARY, and its ItemIcon == its own instance id.)

Scanning EVERY installed archive — **including non-.dat extensions** — for
`{0x856DDBAC, 0x6A386D26, 0xED2174A0}`:
```
[0] 176x44  9855B  <Plugins>\Maxis Buildings\Grutzehaus\LM2x3_Grutzehaus_ed2174a0.SC4Lot  <-- WINS
```
**The art EXISTS, at 1x, inside a `.SC4Lot` file.**

Consequence chain:
1. `TestForKey({856DDBAC, 6A386D26, ED2174A0})` **SUCCEEDS** (the .SC4Lot supplies it).
2. So `replaceIconIfMissing` returns 0xED2174A0 unchanged — **the missing-thumb
   fallback is never invoked for Grutzehaus at all.**
3. The game loads the **1x 176x44** strip from the .SC4Lot.
4. We ship no 2x override for it, so the doubled 88px cell renders a 176x44 strip
   -> the 88px-wide state slice spans TWO 44px states -> **two small icons side by side**.

The 2026-07-29 pass that added the 2x 0x144161EC "fix" therefore shipped a 2x
copy of an asset this code path never requests. Harmless, but inert — which is
exactly why the symptom survived it.

**Why the earlier audit missed it:** its plugin sweep globbed `*.dat` only, so
`.SC4Lot` / `.SC4Desc` / `.SC4Model` DBPF archives were never opened. Same trap
class as the XPCardsHost `*.msi` audit miss.

### All five "art-less" instances have 1x art, all in .SC4Lot
| instance | dims | source |
|---|---|---|
| 0x0D1D6ACB | 176x44 | `Maxis Buildings\Stone House\LM3x3_StoneHouse_0d1d6acb.SC4Lot` |
| 0x2D1E7A9E | 176x44 | `Maxis Buildings\Temple of Grutz\LM6x6_TempleOfGrutz_2d1e7a9e.SC4Lot` |
| 0x2D217719 | 176x44 | `Maxis Buildings\Grutze Industries\LM4x5_GrutzeInd_2d217719.SC4Lot` |
| 0x4D50BA18 | 176x44 | `Maxis Buildings\Longfellow Castle\Longfellow Castle_4d50ba18.SC4Lot` |
| 0xED2174A0 | 176x44 | `Maxis Buildings\Grutzehaus\LM2x3_Grutzehaus_ed2174a0.SC4Lot` |

Full audit: 485 item-icon instances exist in non-ours archives; we shipped 391;
94 gaps — of which exactly **these 5 are plugin-sourced** (menu-reachable via the
CAM DLC landmark exemplars). The other 89 gaps are all stock SimCity_1.dat
entries that are NOT exemplar-bound (and 36 of them are 356x58, a different art
class), so they never populate a menu item button — out of scope, left alone.

This is a pure DATA fix. No hardcoded 1x cell stride is involved (GZWinBtn state
selection is imageWidth/4, proportional — re-confirmed: no icon-dimension
immediates at the three sites), so no upstream code-side report is warranted.

## STEP 4 — fix applied (DONE)

1. Extracted the five 1x strips from their `.SC4Lot` sources (read-only) via
   `DbpfExtract.exe … 0x856DDBAC` -> `tools\itemicons\_work\lots-1x\`.
   Each lot yields TWO PNGs: group `6A386D26` = the 176x44 menu item strip
   (what we want) and group `EBDD10A4` = a 200x200 building query thumbnail
   (different art class, NOT touched).
2. `Upscale2x.exe lots-icons-1x lots-icons-2x --normalize-names`
   -> all five **176x44 -> 352x88**, canonical `T-0x…_G-0x…_I-0x…` naming.
3. Copied into `_work\pack-sub\` (125 -> 130 files, 0 collisions) and
   `DbpfPack.exe pack-sub z_SC4UIScale_ItemIconsSub-2x.dat`
   -> `packed 130 file(s)`, index 7.0, all uncompressed.
4. Re-extract verify: entries=130, pngMagic=130, failures=0; all five plus
   `144161ec` read back at **352x88**.
5. Deployed to `<Plugins>\zzz-SC4UIScale\z_SC4UIScale_ItemIconsSub-2x.dat`
   (SimCity 4 confirmed NOT in tasklist first). 1,497,717 bytes.
6. Post-deploy load-order scan confirms our **352x88 now WINS** over each
   `.SC4Lot` 176x44 for ed2174a0 / 0d1d6acb / 4d50ba18.

Nothing in the mod's or the game's files was modified — all mod/game reads
were read-only. `dist\SC4TouchControls-v1.0.4\` untouched.

Kept the 2x `0x144161EC` (defensive cover for a genuinely art-less icon).

## Suite + docs
- `_tests\Test-DatIntegrity.ps1`: ItemIconsSub expected count **125 -> 130**,
  with a dated comment referencing the Grutzehaus report / task #49 and
  correcting the false "NO icon art anywhere" note.
- `_tests\REGRESSION.md`: new section
  **"DUPLICATED MENU ICON / MISSING-THUMB FALLBACK"** with the trap signature.
- Suite result: **ALL PASS (11 dats + 3 font sources + 2 DLLs + frozen-bundle hash)**

## Out of scope / noted for later
Full audit found 485 item-icon instances in non-ours archives, 391 shipped 2x,
94 gaps. After this fix the remaining 89 gaps are ALL stock `SimCity_1.dat`
entries that are not exemplar-bound (36 of them are 356x58, a different art
class), so they never populate a menu item button. Left alone deliberately.
No code-side/upstream report needed: the blit is proportional (`imageWidth/4`),
so data fully fixes this.

## Reusable instruments written this session
Kept nothing load-bearing in scratchpad. The two scripts worth rebuilding if
needed again (they were scratch, ~60 lines each):
- an all-extension DBPF TGI load-order scanner (walks `<Game>` dats then the
  Plugins tree files-before-subdirs, alphabetical, reporting every archive
  holding a TGI + its PNG IHDR dims, last hit = winner);
- a both-format (`EQZB` binary + `EQZT` text) exemplar property parser.
Consider promoting these into `tools\itemicons\` if a third icon pass happens.
