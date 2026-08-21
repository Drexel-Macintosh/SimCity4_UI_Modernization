# Calling Conventions When Detouring SC4

SimCity 4 is a C++ program compiled for x86 with no public headers, so every
detour into it targets a function whose calling convention and arity are
unknown until proven. Guessing either produces a crash that looks nothing like
its cause, because on x86 the two failure modes corrupt different machinery:
the wrong convention feeds the original function garbage, and the wrong arity
destroys the return address.

## Two failure modes, both silent until the crash

**Wrong arity on a `__thiscall`.** `__thiscall` is callee-cleanup: the called
function issues `ret N` and pops the arguments itself. A typed thunk declared
with the wrong number of stack arguments therefore cleans the wrong number of
bytes, and `ret` lands on whatever the stack happens to hold. The observed
signature is a `PRIV_INSTRUCTION` fault at a garbage EIP with the object's
vtable pointer still sitting in EDX. Counting the visible `push` instructions
at a call site is not a proof of arity — arguments can already be in registers,
in scratch stack slots, or set up in a branch not shown by the excerpt.

**Wrong convention on a virtual.** A virtual member function receives `this` in
ECX, not on the stack. A detour declared `__stdcall(void*)` reads the first
stack slot as `this`, so the original runs against an unrelated value and
dereferences it immediately. The observed signature is an access violation
inside the original function with ECX holding a small integer rather than a
pointer — in one case an `ACCESS_VIOLATION` at `0x0099C4A1` with `ECX = 1`.

## The safe forms

**Detouring a `__thiscall`, which includes every virtual:** declare the detour
as

```cpp
int __fastcall Detour(void* self, void* edx);
```

`__fastcall` places the first integer argument in ECX and the second in EDX, so
`self` receives `this` correctly and `edx` absorbs the register the compiler
would otherwise clobber. It is ignored. Call the original through the same
signature. Append real arguments only after those two, and only when the
signature has been verified against the disassembly — never when it has been
inferred.

**Unknown or unknown arity:** use a naked tail jump rather than a typed
thunk.

```asm
pushad
; record whatever the probe needs here
popad
mov eax, gOrig
jmp eax
```

The stub never returns to itself, so it cleans nothing and assumes nothing
about the argument count or the return convention. It is the only form that is
safe against an arity that has not been proven. Two mechanical notes: MSVC's
inline assembler parses `jmp [symbol]` as a jump to a *label*, so the original's
address must be loaded into a register first; EAX is caller-scratch under
`__thiscall` and is therefore free to use for that.

A typed thunk is appropriate only for slots proven to take zero arguments.

## A vtable slot label in source can be wrong

A slot index recorded in a comment is a claim, not a measurement, and one that
is wrong produces a null indistinguishable from a broken instrument. In build
1.1.641 the slot long documented as the per-class paint entry — index 87 — is
in fact a getter:

```asm
mov eax, [ecx+0x4C]
ret
```

identical across all 23 live UI classes. The real per-class draw is **slot 88**;
for the menu strip its implementation is at `0x0079AA70`. A detour installed on
87 attaches cleanly, never fires, and reports nothing, which reads exactly like
a hook that failed to install.

Before hooking a slot, disassemble the slot's target and confirm it does the
work its label claims. Documentation is the starting point for the search; the
bytes are the answer.
