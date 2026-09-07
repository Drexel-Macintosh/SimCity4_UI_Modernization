# CRASH CENSUS — the game's own exception reports

Source: `Documents\SimCity 4\Exception Reports\`
(read the `.txt` reports only; the `.mdmp` minidumps were not opened).
Census run 2026-09-07 (4.10.0, Unit A3). **20 `.txt` files present, one 0-byte
(2026-08-30 06:45:43) → 19 non-empty crash records.** Of the 19, **5 are
already in the ledger and 14 were never recorded.**

Method (all read-only): each report is parsed for code/module/EIP/registers/
first-16-bytes/top frames/loaded-`SC4UIScale.dll` size. For DLL faults the EIP
bytes are searched in the **shipped** `Plugins\SC4UIScale.dll` (v4.8.0,
`SizeOfImage 0x21F000`) and the rebuilt `build\Release\SC4UIScale.dll` by
converting file offset → RVA through the PE section table, and the mod's own
log strings that follow the match confirm the function. The `build\Release`
PDB matches (`SymType SymPdb`, `PdbUnmatched false`) but ships **public symbols
only** — internal probe functions (`LogBubbleCallStack`, `SpGetterLog`, …) are
`static`/anonymous-namespace and carry no public record, so naming is by byte
pattern + the trailing log-string literal, cross-checked against the ledger.

## The table

| # | when | code | fault module | EIP | RVA (Sec:Off) | ECX / ESI / EAX | first 16 bytes @ EIP | top 3 frames | DLL image size | ledgered? |
|---|------|------|--------------|-----|---------------|-----------------|----------------------|--------------|----------------|-----------|
| 1 | 2026-08-05 15:48:39 | AV c0000005 | SimCity 4.exe | 0x00884fe1 | 0x484fe1 (01:0x47dfe1) | 0 / 02fa0020 / 0 | `c6 44 08 01 00 8b 96 14 01 00 00 8b 86 1c 01 00` | exe 01:0047dfe1; GZDll+580630; GZDll+134413 | 1,581,056 | no |
| 2 | 2026-08-05 15:56:54 | AV | SimCity 4.exe | 0x00884fe1 | 0x484fe1 | 0 / 02f80020 / 0 | `c6 44 08 01 00 …` | exe 01:0047dfe1; GZDll+580630; GZDll+134413 | 1,581,056 | no |
| 3 | 2026-08-05 16:01:05 | AV | SimCity 4.exe | 0x00884fe1 | 0x484fe1 | 0 / 031d0020 / 0 | `c6 44 08 01 00 …` | exe 01:0047dfe1; GZDll+580630; GZDll+134413 | **DLL not loaded** | no |
| 4 | 2026-08-05 16:02:06 | AV | SimCity 4.exe | 0x0098e9a6 | 0x58e9a6 (01:0x5879a6) | 0 / 030e8b14 / 00adaa58 | `8b 41 4c 83 c1 4c ff 60 3c cc 8b 81 e4 00 00 00` | GZDll+527273; GZDll+587663; exe 01:00472f8e | **DLL not loaded** | no |
| 5 | 2026-08-05 16:03:08 | AV | SimCity 4.exe | 0x0098e9a6 | 0x58e9a6 | 0 / 03028b14 / 00adaa58 | `8b 41 4c 83 c1 4c …` | GZDll+527273; GZDll+587663; exe 01:00472f8e | **DLL not loaded** | no |
| 6 | 2026-08-05 16:04:54 | AV | SimCity 4.exe | 0x0098e9a6 | 0x58e9a6 | 0 / 030b8b14 / 00adaa58 | `8b 41 4c 83 c1 4c …` | GZDll+527273; GZDll+587663; exe 01:00472f8e | **DLL not loaded** | no |
| 7 | 2026-08-05 16:10:46 | AV | SimCity 4.exe | 0x0098e9a6 | 0x58e9a6 | 0 / 02f78b14 / 00adaa58 | `8b 41 4c 83 c1 4c …` | GZDll+527273; GZDll+587663; exe 01:00472f8e | **DLL not loaded** | no |
| 8 | 2026-08-05 16:11:12 | AV | SimCity 4.exe | 0x0098e9a6 | 0x58e9a6 | 0 / 030a8b14 / 00adaa58 | `8b 41 4c 83 c1 4c …` | GZDll+527273; GZDll+587663; exe 01:00472f8e | **DLL not loaded** | no |
| 9 | 2026-08-14 15:01:28 | **PRIV_INSTRUCTION c0000096** | (none) | 0x36363c2a | — (heap) | 36363c18 / 00825d60 / 77db9fdc | `6e 8a 96 00 00 00 63 01 00 00 98 01 00 00 cd 04` | (stack only, no symbolised frames) | 1,597,440 | **yes — #156** |
| 10 | 2026-08-14 15:02:03 | **PRIV_INSTRUCTION** | (none) | 0x363434ac | — (heap) | 00825d5f / 511502c9 / 1ae25d15 | `f4 01 00 00 f4 01 00 00 00 00 00 00 00 00 00 00` | 00:00000000 | 1,597,440 | **yes — #156** |
| 11 | 2026-08-14 16:06:19 | AV | SimCity 4.exe | 0x0099c4a1 | 0x59c4a1 (01:0x5954a1) | 1 / 36020e18 / 1d430ea0 | `83 7b 64 00 0f 84 48 02 00 00 8b 03 83 65 f8 00` | GZDll+583332; **SC4UIScale 01:0000482b**; GZDll+580644 | 1,605,632 | **yes — #156** |
| 12 | 2026-08-18 08:30:43 | AV | **SC4UIScale.dll** | 0x6ff3bc8a | **0x2bc8a** (01:0x2ac8a) | 00e20000 / 00c90f91 / 00400000 | `80 7e fb e8 74 18 80 7e fe ff 74 12 80 7e fd ff` | SC4UIScale 01:0002ac8a; exe 01:001e191c; exe 03:0005b698 | 1,691,648 | **no** |
| 13 | 2026-08-18 15:43:51 | AV | **SC4UIScale.dll** | 0x6e149a29 | **0x29a29** (01:0x28a29) | 38 / 0 / 030f0124 | `8b 33 2b f2 81 c6 00 00 40 00 e8 18 6d 00 00 83` | SC4UIScale 01:00028a29; SC4UIScale 01:00028aaf | 1,691,648 | **yes — power-plant probe** |
| 14 | 2026-08-18 15:44:35 | AV | **SC4UIScale.dll** | 0x6ff39a29 | **0x29a29** | 38 / 0 / 03020010 | `8b 33 2b f2 81 c6 00 00 40 00 …` | SC4UIScale 01:00028a29; SC4UIScale 01:00028aaf | 1,691,648 | **yes — power-plant probe** |
| 15 | 2026-08-23 17:36:22 | AV | SimCity 4.exe | 0x007b4683 | 0x3b4683 (01:0x3ad683) | 410 / 0 / 15a | `8b 55 00 8b cd 89 44 24 18 ff 92 8c 00 00 00 33` | (stack only) | 2,039,808 | no |
| 16 | 2026-08-23 17:36:48 | AV | SimCity 4.exe | 0x007b4683 | 0x3b4683 | 410 / 0 / 15a | `8b 55 00 8b cd …` | (stack only) | 2,039,808 | no |
| 17 | 2026-08-23 17:40:51 | AV | SimCity 4.exe | 0x007b4683 | 0x3b4683 | 410 / 0 / 15a | `8b 55 00 8b cd …` | (stack only) | 2,039,808 | no |
| 18 | 2026-08-30 06:45:43 | — | — | — | — | — | **(0-byte file — no record)** | — | — | n/a |
| 19 | 2026-08-31 13:08:52 | AV | **SC4UIScale.dll** | 0x6f329000 | **0x49000** (01:0x48000) | 00400000 / 00d634ac / 5 | `80 7e fb e8 74 18 80 7e fe ff 74 12 80 7e fd ff` | SC4UIScale 01:00048000; exe 01:001e191c | 2,224,128 | **no** |
| 20 | 2026-09-01 10:58:47 | AV | SimCity 4.exe | 0x0099d757 | 0x59d757 (01:0x596757) | 009d6610 / 009d6610 / e904e983 | `ff 90 fc 00 00 00 50 ff 75 f8 ff 55 0c 83 c4 10` | GZDll+588122; **SC4TouchControls 01:00006bd4**; GZDll+588135 | 2,224,128 | no |

`GZDll+N` = the game's own `GZDllGetGZCOMDirector() + N` symbolic frames (its
only exported symbol; the offsets are into `SimCity 4.exe`, not our DLL).

## What maps, and to what

### (a) Faults inside SC4UIScale.dll — 4 reports, 2 functions

**`LogBubbleCallStack` — #12 (08-18 08:30) and #19 (08-31 13:08).** Both hold
the identical 16 bytes `80 7e fb e8 74 18 80 7e fe ff …` =
`cmp byte ptr [esi-5],0E8h / je / cmp byte ptr [esi-2],0FFh / …` — the
return-address sniffer's `c[-5]==0xE8 || c[-2]==0xFF` cascade. Confirmed
positively: the byte window is present in the **shipped v4.8.0**
`Plugins\SC4UIScale.dll` at file 0x48400 / **RVA 0x49000**, immediately
followed by `push "CodePatches: BUBBLESTACK%s."` and two
`push "mission_selection"` — the exact log line and gate string of that
function. #19's own RVA is **0x49000**, i.e. that build's `LogBubbleCallStack`
verbatim; #12 is the same instruction cascade in the older `SizeOfImage`
0x19D000-era build (RVA 0x2bc8a). The read is speculative: `esi` walks raw
stack words looking for bytes that follow a `call`, so `[esi-5]` steps off
mapped memory. **These two share the pattern the task flagged; no other report
shares the `80 7e fb e8` bytes.**

**`SpGetterLog` — #13 (08-18 15:43) and #14 (08-18 15:44).** Identical bytes
`8b 33 2b f2 81 c6 00 00 40 00` = `mov esi,[ebx] / sub esi,eax /
add esi,0x400000` — read a vtable then rebase it to the game's image base, the
signature of `SpGetterLog`'s `PROXYGET30` path. RVA **0x29a29**, ECX=0x38 —
exactly as the ledger already recorded (REGRESSION.md §"CRASH placing a power
plant", 2026-08-18: "Section:Offset 0x01:0x00028a29, ECX=0x38"). These bytes
are **absent** from the current shipped DLL because that fault was fixed by
wrapping both derefs in `__try` (v3.x); the crash bytes survive only in these
two reports.

### (b) Faults in SimCity 4.exe — 8 reports, 4 addresses, no existing attribution

All exe bytes below were confirmed byte-exact against the installed
`SimCity 4.exe` (`TimeDateStamp 0x4C12BFB7`), and **none** of the four RVAs
(nor their `0x00…`/bare-hex forms) appears anywhere in `docs\` or
`_tests\REGRESSION.md`:

* **0x00884fe1** (#1-3, RVA 0x484fe1) — `mov byte ptr [eax+ecx+1],0` inside a
  jump-table byte-fill (`sub_884FB0`), reached with EAX=ECX=0 → writes to
  address 0x1. Null base.
* **0x0098e9a6** (#4-8, RVA 0x58e9a6) — `mov eax,[ecx+4C] / add ecx,4C /
  jmp [eax+3C]`, a virtual dispatch with **ECX=0** (null `this`) →
  `[0x4C]` faults. Tiny thunk `sub_98E9A0`.
* **0x0099c4a1** (#11, RVA 0x59c4a1) — `cmp dword ptr [ebx+64],0 / je /
  mov eax,[ebx]` with a garbage EBX. The faulting function begins at ~0x99C490
  (`push ebp;mov ebp,esp` at file −24), i.e. immediately adjacent to
  `PlotPresent` (`0x0099C498`, `docs\DECOMPILATION-STATUS.md:289`). See §(d).
* **0x007b4683** (#15-17, RVA 0x3b4683) — `mov edx,[ebp] / call [edx+8C]`, a
  virtual call through a bad object, ECX=0x410.
* **0x0099d757** (#20, RVA 0x59d757) — `call [eax+FC]` virtual call; ECX=ESI=
  0x9D6610. See §(d) — the stack is dominated by **SC4TouchControls.dll**.

> ⚠ **The 0x00910010 minimap-bake family is NOT in this folder.** The ledger's
> #109/#121 crashes (REGRESSION.md:5262-5268 and 5437-5460) were six reports
> dated **08-03 20:09 → 08-04 15:29**, all faulting at `0x00910010` (`rep stosd`
> in the game's row fill, product 384/768 = the 1.5×/3× window width). **None of
> those files survive in the folder today** — the oldest present is 08-05
> 15:48. The surviving 08-05 cluster (#1-8) faults at unrelated addresses
> (0x884fe1, 0x98e9a6) and, for #3-8, **with SC4UIScale.dll not even loaded** —
> so it cannot be the minimap family and cannot be ours.

### (c) The two 08-14 PRIV_INSTRUCTION reports execute at heap — unmapped

**#9 (15:01) EIP 0x36363c2a, #10 (15:02) EIP 0x363434ac** — both far outside
any module (Section:Offset 0x00:0x0, "Exception module: ."), executing in heap/
data, so no RVA and no byte→function map is possible. Recorded **unmapped**.
Loaded `SC4UIScale.dll` image size **1,597,440** places them in the mid-August
(≈v2.9x) build era. These are the crashes the ledger's **#156** section
(2026-08-14) already owns: "A CRASH WAS SHIPPED CHASING THIS (PRIV_INSTRUCTION,
garbage EIP…)" and "both crashes today came from inferring a signature
(PRIV_INSTRUCTION from a wrong arity, ACCESS_VIOLATION from `__stdcall`…)". The
paired ACCESS_VIOLATION that sentence refers to is **#11** (16:06, 0x99c4a1),
which carries an `SC4UIScale.dll 01:0000482b` frame in its stack — so all three
08-14 reports are the #156 hook-signature episode.

### (d) Ledger coverage (grepped each timestamp in `HH.MM`/`HH:MM` and each RVA)

| report | in ledger? | where |
|---|---|---|
| 08-14 15:01, 15:02, 16:06 | **yes** | #156, 2026-08-14 (by description; #11's RVA/frame corroborates) |
| 08-18 15:43, 15:44 | **yes** | "CRASH placing a power plant", 2026-08-18 (RVA 0x28a29, ECX=0x38 verbatim) |
| 08-05 ×8 | no | — (and #3-8 ran without our DLL) |
| 08-18 08:30 (`LogBubbleCallStack`) | no | — distinct from the 15:43 power-plant crash |
| 08-23 ×3 (0x7b4683) | no | — (only doc dated 08-23 is the Disaster-Flyout rebuild; no crash) |
| 08-31 13:08 (`LogBubbleCallStack`) | no | — |
| 09-01 10:58 (0x99d757) | no | — |

**Never ledgered: 14 of the 19 non-empty reports.**

## Shared byte-pattern groups (beyond the pair the task named)

Five EIP-byte signatures recur; only the third is inside our DLL:

1. `c6 44 08 01 00 …` (exe 0x884fe1) — #1, #2, #3
2. `8b 41 4c 83 c1 4c …` (exe 0x98e9a6) — #4, #5, #6, #7, #8
3. `80 7e fb e8 74 18 …` (**`LogBubbleCallStack`**, DLL) — #12, #19
4. `8b 33 2b f2 81 c6 …` (**`SpGetterLog`**, DLL) — #13, #14
5. `8b 55 00 8b cd …` (exe 0x7b4683) — #15, #16, #17

## Build-era fingerprint (loaded SC4UIScale.dll SizeOfImage)

1,581,056 (Aug 5) → 1,597,440 / 1,605,632 (Aug 14) → 1,691,648 (Aug 18) →
2,039,808 (Aug 23) → **2,224,128 (Aug 31 & Sep 1)**. The last value equals the
shipped **v4.8.0** `Plugins\SC4UIScale.dll` (`SizeOfImage 0x21F000` = 2,224,128),
confirming #19/#20 are the v4.8.0-era binary. The current `build\Release` DLL is
newer still (`SizeOfImage 0x225000`, rebuilt 2026-09-07 07:26 — the in-flight
v4.10.0 tree), which is why the older crash bytes are not all byte-exact
in `build\Release` while they are exact in the deployed v4.8.0 DLL.

## The rule this census establishes

**An exception report younger than the last ledger entry blocks a release.**
The game writes these files for free and they sat unread; two of our own probe
crashes (`LogBubbleCallStack`, 08-18 and 08-31) were never recorded and one
(`SpGetterLog`) had already been diagnosed but a *second* unguarded probe kept
crashing after it. **The release checklist reads
`Documents\SimCity 4\Exception Reports\` first** and no release ships while a
`.txt` there is newer than this ledger's last dated entry, until each new report
is triaged into REGRESSION.md. (This is the standing law "read the game's OWN
exception report" made into a gate.)

Companion build gate: **`_tests\Test-ProbeDerefGuards.py`** fails the build on
any raw `*reinterpret_cast<void**/void***/uintptr_t*>` vptr read, `vt[…]`/
`dvt[…]`/`pv[…]` slot call, or `x[-N] == 0xHH` stack peek inside probe/detour
code (function name matching `Log|Detour|Thunk|Probe|Cap|Census|Scan`, `Sp*`,
or any function calling `_ReturnAddress()`) that sits outside a `__try` or a
`ProbeSafe` helper — the exact shape that produced #12/#13/#14/#19. `- base +
kImageBase` rebases and fixed-`.data` reads are reported as info only; a
`// deref-ok: <reason>` waiver keeps a site visible in its own list.
