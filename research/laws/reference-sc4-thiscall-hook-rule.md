---
name: reference-sc4-thiscall-hook-rule
description: "SC4 hooking: NEVER guess a calling convention or arity. Two crashes in one session. __thiscall detour = __fastcall(self, edx); unknown arity = naked tail jmp."
metadata:
  type: reference
---

**TWO CRASHES IN ONE SESSION (2026-08-14), same root cause: I inferred a
calling convention from a disassembly excerpt instead of using a form that
cannot be wrong.**

1. **PRIV_INSTRUCTION**, garbage EIP, EDX still holding the buffer vtable.
   Hooked buffer slot 20 with a TYPED thunk declared with two stack args,
   counted from two visible `push`es. `__thiscall` is CALLEE-CLEANUP: a wrong
   arity cleans the wrong number of bytes and `ret` lands in nowhere.
2. **ACCESS_VIOLATION at 0x0099C4A1 with ECX = 1.** Detoured `PlotPresent`
   (a VIRTUAL) as `__stdcall(void*)`. `this` arrives in **ECX**, not on the
   stack, so the original ran against garbage and dereferenced it immediately.

## The rules

- **Detouring a `__thiscall` (any virtual):** write
  `int __fastcall Detour(void* self, void* edx)`. `ecx` maps to `self`, `edx`
  is ignored. Call the original the same way. Add real args AFTER those two
  only when the signature is KNOWN, not inferred.
- **Unknown or unverified arity:** use a **NAKED TAIL JMP**
  (`pushad` / note / `popad` / `mov eax, gOrig` / `jmp eax`). It never returns
  to the thunk, so it cleans nothing and makes no assumption at all. Pattern
  already shipping at `CodePatches.cpp` X8DispatchStub. Note MSVC parses
  `jmp [symbol]` as a LABEL - load into a register first; EAX is scratch in
  `__thiscall`.
- `UiSpike.cpp` already says only ZERO-ARG slots may be hooked with a typed
  thunk. **Read that note before hooking anything.**

## And the slot table itself can be wrong

`UiSpike.cpp` asserted "GZPaint is vtable INDEX 87". In build 1.1.641 slot 87
is `mov eax,[ecx+0x4C]; ret` - a getter, identical across all 23 live UI
classes. The real per-class draw is **slot 88** (`0x0079AA70` for the menu
strip). Hooking 87 installs cleanly and fires zero times, a null that looks
exactly like a broken instrument. Grep the docs first, then **verify the
load-bearing line against the bytes**.

Related: [[feedback-check-our-previous-work-first]], [[feedback-null-is-not-evidence]]
