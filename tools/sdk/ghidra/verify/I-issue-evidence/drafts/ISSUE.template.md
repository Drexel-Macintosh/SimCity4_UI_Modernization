<!-- DRAFT for nsgomez/gzcom-dll. NOT POSTED. Assembled by assemble_drafts.py; edit this template, not the output. -->
**Title:** Some methods in cIGZWin.h, cIGZApp.h and cIGZCOMDirector.h are in a different order from the game, so calls run the wrong function

Hi, and thanks for gzcom-dll. Our mod (SimCity 4 UI Modernization) is built on it. While working with the window interface, we found three headers that don't match the game in places. We have checked every method in them against the game, and we've prepared a fix.

## The problem in plain terms

Every object in SimCity 4 has a numbered list of the functions it offers. In C++ this list is the vtable, and each position in it is a *slot*.

A plugin never calls a game function by its name. The compiler turns `window->GZWinMoveTo(x, y)` into "call the function in slot 56 of this window's list", and it works out that number from the order the methods are declared in the header.

So when the header's order doesn't match the game's, the plugin quietly calls a different function. It compiles without any warning, and then the game does something else.

## What we found

| Header | Methods that reach the wrong function | What it looks like |
|---|---|---|
| `cIGZWin.h` | **40 of 144**, plus **9** whose arguments don't match the game | `GZWinMoveTo(x, y)` moves a window *by* x and y instead of *to* them. `GetArea()` and `GetArea(cRZRect&)` are swapped. Every mouse and keyboard handler is one slot off. |
| `cIGZApp.h` | **8 of 12** | `FrameWork()` returns the text "SimCity 4" instead of the framework. `ModuleName()` runs `AddApplicationService`. |
| `cIGZCOMDirector.h` | **1** | Slot 13 is `GetDirectorID` in the game, not `AddDirector`. |

**The fix** is on a branch in our fork, in three commits (one per header): https://github.com/Drexel-Macintosh/gzcom-dll/tree/fix-vtable-order
- With it, every method in these three headers compiles to the game's slot, with the game's argument sizes.
- All 31 files in `gzcom-dll/src` still compile.
- We'll open it as a pull request alongside this issue.

⚠ **One behaviour change:** with the fix, `GZWinMoveTo` really moves a window *to* (x, y). Plugins that worked around the bug by passing offsets should call the new `GZWinOffset(dx, dy)` instead.

## How we checked

For each method we checked two things separately. A method only counts as wrong when the two disagree.

1. **Where the header sends the call.** We compiled small test files against the header with MSVC and read which slot each call uses. We read it two different ways, and they agree for every method.
2. **What the game has in that slot.** We read the game's own code at every slot and worked out what each function does, for example "copies the window's rectangle into the argument" or "moves all four edges by dx, dy".
   - Where functions call each other, the calls confirm the identities too. For example, `PullToFront` calls `ChildToFront`, and `SetCursor` calls `UpdateCursor`.
   - For the mouse and keyboard handlers we used the game's message dispatcher. It shows which slot handles which message, and exactly what it passes.

**The game we measured** is `SimCity 4.exe` 1.1.641.0, Steam edition (SHA-256 `f512a405c1e3f0dc82b784d5d9619f4751f03d0905d9d6b94cd528f1d4be1153`). The GOG edition is a different file. A GOG decompilation publishes six code addresses, and the Steam exe has the same code at all six.

The scripts are public and re-run against your own copy of the game (links at the end).

## 1. cIGZWin.h

### Why it happens

MSVC does something surprising with overloads (several virtual methods with the same name). It puts all of them together at the slot of the first one declared, **in reverse order**. The header runs into this in three places:

- **`SetSize(cRZPoint)` is pulled up the list.**
  - It's declared near the end, but MSVC moves it next to `SetSize(int32_t, int32_t)` at slot 53. In the game the two are far apart, at 53 and 118.
  - This pushes the methods just after it down one slot.
  - Everything declared after its original spot ends up one slot too early.
- **`GZWinOffset(dx, dy)` is missing.**
  - The game has it at slot 57, right after `GZWinMoveTo`. Because the header doesn't declare it, the header's `GZWinMoveTo` lands on slot 57, so a window moves *by* the numbers instead of *to* them.
  - The missing slot also cancels the push from the first point, which is why slots 58 to 117 happen to line up.
- **Overload groups written in the game's order come out backwards.**

### What goes wrong, for example

- `GZWinMoveTo(x, y)` moves the window by (x, y).
- `SetSize(w, h)` runs `SetArea(const cRZRect&)`, which treats the width as a memory address.
- `GetArea()` runs `GetArea(cRZRect&)`, which writes 16 bytes through whatever pointer happens to be on the stack.
- `GetArea(cRZRect&)` runs `GetArea()` and never fills in your rectangle.
- A window class written against this header receives each mouse and keyboard event in the handler declared just after the right one.
- `SendMsg` and `PostMsg` reach the wrong overload. The 5-argument `SendMsg` runs the `GZOnCommand` handler.

### The 40 methods that reach the wrong function

{TABLE}

A few of the game's default handlers share one small function (one per argument size), so the same address appears more than once in the last column.

### The 9 methods whose arguments don't match the game

Even in the right slot, these would break, because the game's function takes different arguments.
- We compared argument sizes at every slot where the game's code shows how much it takes off the stack: 142 of the 148 slots.
- The last two rows were found by reading the code, because a pointer and a 4-byte colour take the same space.

| Method | Game slot | The header passes | The game takes |
|---|---:|---|---|
| `AccelerateKeyboardMsg()` | 77 | nothing | the message, which it passes on to the key accelerator |
| `CheckKeyEquivalent(uint32_t)` | 80 | 1 argument | 2: the key and the modifiers |
| `GZOnSetFocus(uint32_t, uint32_t)` | 132 | 2 arguments | 1: the window that lost focus |
| `GZOnMouseWheel(int32_t, int32_t, uint32_t)` | 139 | 3 arguments | 4, where the 4th is the wheel delta |
| `GZOnCaptureChanged(cIGZWin*, uint32_t, uint32_t, uint32_t)` | 140 | 4 arguments | 2 |
| `GZOnMouseEnter(uint32_t, uint32_t)` | 141 | 2 arguments | 1: the window the mouse left |
| `GZOnCommand(uint32_t)` | 143 | 1 argument | 2 |
| `SetFillColor(cRZColor const&)` | 105 | a pointer to the colour | the colour itself, by value |
| `SetShadeColor(cRZColor const&)` | 111 | a pointer to the colour | the colour itself, by value |

### When it started

Commit `387a9751` ("Fix the ordering of a few overloads in cIGZWin") changed several of these. We compiled the header just before it (`4669fa92`) and after it:

- **It broke** the `GetArea` / `GetAreaAbsolute` pairs (slots 47–50) and the fill-colour overloads (102–107). All eight were right before, and are backwards now.
- **It also broke `CenterWindowInRect(cRZRect*)`.** Before, it reached `CenterWindowInRect(const cRZRect&)`, which takes the same pointer, so it worked. Now it reaches `SetSize(cRZPoint)` and resizes the window instead.
- **It fixed** `SetArea(l, t, r, b)`.
- **`SetArea(const cRZRect&)` was wrong before and is still wrong.** It now reaches `GZWinMoveTo`.

The rest of the 40 were already wrong before that commit.

## 2. cIGZApp.h

**Where the game's table comes from:**
- The framework keeps its app object at `0x00B540B4`. At startup the game stores `new cSC4App` there, at offset `0x2C` (from `0x0044C214`).
- That object's function list is at `0x00A86A68`.
- The framework's base class `cGZApp` has its own list, at `0x00AC3190`. Its simple default versions show what each function returns.

| Slot | The game has | How we know | `cIGZApp.h` has |
|---:|---|---|---|
| 3 | `AsIGZSystemService` | returns the object's system-service part | same |
| 4 | `AddApplicationService(cIGZSystemService*)` | gets the framework from slot 10 and passes the argument to its `AddSystemService` | `ModuleName` |
| 5 | `ModuleName` | returns the name saved by the constructor, "SimCity 4" | `FrameWork` |
| 6 | `PreFrameWorkInit` | called at startup (`0x0087AFDD`); if it returns false, the framework shuts COM down | `AddApplicationService` |
| 7 | `PostFrameWorkInit` | called later in startup, after the app has initialised (`0x0087B09C`) | `PreFrameWorkInit` |
| 8 | `GZRun` | called to run the game (`0x0087959C`); SimCity 4's returns false, so the framework runs its own loop | `PostFrameWorkInit` |
| 9 | `PreFrameWorkShutdown` | called at shutdown (`0x0087AB54`) | same |
| 10 | `FrameWork` | returns the framework pointer (`0x00B540AC`) | `GZRun` |
| 11–13 | the three `...Here()` hooks | one shared empty function; startup calls slots 13, 12 and 11 in that order | 11 `LoadRegistry`, 12 `AddDynamicLibrariesHere`, 13 `AddCOMDirectorsHere` |
| 14 | `LoadRegistry` | the only one of slots 11–14 that returns a `bool`; SimCity 4's version reads `Resources.ini` and sets up the resource files | `AddApplicationServicesHere` |

**One thing the game can't show:** SimCity 4 implements the three `...Here()` hooks as one shared empty function, so their order among slots 11–13 isn't visible. The Mac version's debug symbols give 11 `AddDynamicLibrariesHere`, 12 `AddCOMDirectorsHere` and 13 `AddApplicationServicesHere`, and the fix uses that order.

**What goes wrong:**
- `FrameWork()` returns the text "SimCity 4" instead of the framework.
- `ModuleName()` runs `AddApplicationService` with a garbage argument, and leaves the caller's stack 4 bytes off.
- `AddApplicationServicesHere()` re-runs the game's resource setup.

The fix also corrects the comment on `LoadRegistry`: the base version returns true, not false.

## 3. cIGZCOMDirector.h

In the game, slot 13 of every COM director's function list is `GetDirectorID`:
- We found 27 director function lists, which all share the base class's functions in slots 9–12, 14 and 15.
- In 26 of them, slot 13 is a one-line function that returns a constant, a different constant in each. The 27th belongs to an abstract class and has the "pure virtual" placeholder there.
- One of them, `0x00AD8BA0` (the resource manager's director), returns `0xC3CAEC3B`. That is the same ID Scion uses for `cGZResManCOMDirector`.
- None of the 27 has a slot for `AddDirector` at all. Slot 16 is the destructor. (One list has an extra 17th entry, which is a different function.)

In gzcom-dll, `cIGZCOMDirector.h` puts `AddDirector` at slot 13, and `cRZCOMDllDirector.h` adds `GetDirectorID` after the destructor, at slot 17.

**What goes wrong: nothing you'd notice today.** The game never calls slot 13 on a plugin's own director; if it did, every gzcom-dll plugin would crash. It matters only for code that uses one of the game's own directors:
- Calling `AddDirector` on one through `cIGZCOMDirector*` actually runs its `GetDirectorID`.
- Calling `GetDirectorID` through `cRZCOMDllDirector*` reads slot 17, which is past the end of the game's list.

**A note, in case the header came from the Mac symbols:** the Mac type archive in sc4-ghidra-symbols does list `AddDirector` at slot 13 for `cIGZCOMDirector`, but the Windows game doesn't have it there. The same archive's `cRZCOMDllDirector` leaves slot 13 unnamed.

## Scope

- **`cIGZWin.h`: all 144 methods checked.** 40 are wrong (listed above) and 104 are right.
- **`cIGZApp.h`: all 12 checked.** The order of the three empty hooks comes from the Mac symbols, as explained above.
- **`cIGZCOMDirector.h`: all 13 checked.**
- **Game version:** measured on the Steam edition of 1.1.641. The GOG edition matches at the six addresses we could compare.

## Evidence

Everything above can be re-run against your own copy of the game:
https://github.com/Drexel-Macintosh/SimCity4_UI_Modernization/tree/main/tools/sdk/ghidra/verify/I-issue-evidence
- `consolidate_cigzwin.py`: the `cIGZWin` table and argument lists.
- `regression_387a9751.py`: what 387a9751 changed.
- `app_director.py`: the `cIGZApp` and director tables.
- `verify_fixed_headers.py`: checks the fix branch, method by method.
