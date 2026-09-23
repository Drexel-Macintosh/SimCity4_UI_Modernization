<!-- DRAFT for nsgomez/gzcom-dll. NOT POSTED. Every row re-runs with I-issue-evidence/app_director.py. -->
**Title:** cIGZApp.h: method order doesn't match SimCity 4 1.1.641 (8 of 12 on the wrong slot)

`cIGZApp.h` declares the app interface in an order the game doesn't use. 8 of its 12 methods compile to a slot that holds a different method. Scion's `cIGZApp.h` and the Mac build's debug symbols both have the game's order.

**Where the game's table comes from:**
- The framework stores the app pointer at `0xB540B4`.
- Its only setter call (`0x0044C214`) passes `new cSC4App` + 0x2C.
- The constructor puts vtable `0x00A86A68` at +0x2C.
- The framework's own default class `cGZApp` has its cIGZApp vtable at `0x00AC3190`. Its default bodies show each slot's return type.

| slot | game | evidence | cIGZApp.h has |
|---:|---|---|---|
| 3 | `AsIGZSystemService` | `lea eax,[ecx-0x1C]; ret` | same |
| 4 | `AddApplicationService(cIGZSystemService*)` | calls its own slot 10 for the framework, then jumps to `cIGZFrameWork::AddSystemService` with the caller's argument | `ModuleName` |
| 5 | `ModuleName` | returns `[this+8]`, the name string the constructor stored (`"SimCity 4"`) | `FrameWork` |
| 6 | `PreFrameWorkInit` | framework init `0x0087AFDD`: no argument, the bool is tested, and on false it calls `RealShutdown` | `AddApplicationService` |
| 7 | `PostFrameWorkInit` | framework init `0x0087B09C`, after `AppInit`/`PostAppInit` | `PreFrameWorkInit` |
| 8 | `GZRun` | `0x0087959C` calls it on `Application()`. Both classes return false, and the framework then runs its own loop | `PostFrameWorkInit` |
| 9 | `PreFrameWorkShutdown` | framework shutdown `0x0087AB54` | same |
| 10 | `FrameWork` | `jmp 0x008793EC` = `mov eax,[0xB540AC]; ret` | `GZRun` |
| 11–13 | the three `void` `…Here()` hooks | an empty `ret` in both classes. Framework init calls 13, 12, 11 in that order | 11 = `bool LoadRegistry` |
| 14 | `bool LoadRegistry()` | `mov al,1; ret` in `cGZApp`. SimCity 4's version reads `Resources.ini`, sets up the DB segments, and returns `al=1`. It is the only bool among 11–14 | `AddApplicationServicesHere` |

**Slots 11–13.**
- SimCity 4 implements all three hooks as the same empty function, in both `cGZApp` and `cSC4App`, so the game can't show their order relative to each other.
- The Mac symbols (and Scion) give 11 `AddDynamicLibrariesHere`, 12 `AddCOMDirectorsHere`, 13 `AddApplicationServicesHere`.

**Consequence:** a plugin that calls `ModuleName()` through this header actually calls `AddApplicationService` with a garbage argument. `FrameWork()` returns the module name, and `AddApplicationServicesHere()` re-runs SimCity 4's resource setup.

**Evidence:** `tools/sdk/ghidra/verify/I-issue-evidence/app_director.py` at https://github.com/Drexel-Macintosh/SimCity4_UI_Modernization re-derives the table from the exe and fails if any row stops holding.
