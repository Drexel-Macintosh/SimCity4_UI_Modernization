<!-- DRAFT for nsgomez/gzcom-dll. NOT POSTED. Every row re-runs with I-issue-evidence/app_director.py. -->
**Title:** cIGZCOMDirector.h: slot 13 is GetDirectorID in SimCity 4, not AddDirector

`cIGZCOMDirector.h` declares `AddDirector(cIGZCOMDirector*)` at slot 13, and `cRZCOMDllDirector.h` adds `GetDirectorID()` after the destructor, at 17. In the game, slot 13 is `GetDirectorID()` and `AddDirector` is not virtual. Scion's `cIGZCOMDirector.h` has the game's layout.

**The game's director vtables** (SimCity 4 1.1.641):
- 27 vtables share the base class's implementations of slots 9–12 and 14–15 (`RefCount`, `RemoveRef`, `FrameWork`, `GZCOM`, `GetLibraryPath`, `GetHeapAllocatedSize`).
- In 26 of them, slot 13 is `mov eax, imm32; ret` with a different constant each time. The 27th is abstract.
- One is `0x00AD8BA0`, the resource manager's director: its slot 13 returns `0xC3CAEC3B`, Scion's `kGZResManCOMDirectorID`.
- Slot 16 is the scalar deleting destructor, and the vtable ends there, so there is no slot for `AddDirector` at all.

**Consequence.**
- Plugin directors built from this header carry `AddDirector` at 13 and `GetDirectorID` at 17.
- The game evidently never calls slot 13 on a plugin's director. If it did, every gzcom-dll plugin would run `AddDirector` on a garbage pointer, so today the defect is latent.
- It bites code that calls `GetDirectorID()` or `AddDirector()` through a `cIGZCOMDirector*` that points at one of the game's own directors.

**Possible fix.**
- Declare `GetDirectorID()` in `cIGZCOMDirector` after `GZCOM()`, and make `AddDirector` a non-virtual member of `cRZCOMDllDirector`, as Scion does.
- The destructor stays at 16, where the game has it.

**Evidence:** `tools/sdk/ghidra/verify/I-issue-evidence/app_director.py` at https://github.com/Drexel-Macintosh/SimCity4_UI_Modernization lists all 26 constants and fails if any row stops holding.
