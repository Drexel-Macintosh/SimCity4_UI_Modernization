<!-- DRAFT for nsgomez/gzcom-dll. NOT POSTED. Assembled by assemble_drafts.py; edit this template, not the output. -->
**Title:** cIGZWin.h: 40 declarations compile to the wrong vtable slot for SimCity 4 1.1.641, and 8 argument lists don't match

Compiled with MSVC, `cIGZWin.h` at HEAD (`779b669b`) puts 40 of its 147 declarations on a vtable slot where the game has a different method. A call through the header runs that other method. Where the two argument lists differ in size, the callee also pops the wrong number of bytes.

### How it was checked
- **Header:** the slot MSVC assigns to each declaration, read two ways: from the call-site displacement, and from the member-pointer thunk. The two readings agree on all 147.
- **Game:** each slot was identified from its own code in the base `cGZWin` vtable at `0x00ADC8D8`. The slots in 50–60, 63–70, 86–89 and 115–150 were also compared across 15 window classes. The input handlers were identified from `DoMessage`'s dispatch table (`0x0099CEF9`). The exe is the Steam 1.1.641 build.
- **Controls:** the game-side identification agrees with what a shipping plugin relies on at runtime. It calls `GetW` (41) through this header, and it hooks `SetFlag` (68, `0x0099DB6B`) and `PlotPresent` (124, `0x0099C498`) by address; those hooks fire on the expected calls.

### The 40
{TABLE}

The base class's default input handlers share a few stub functions (one per argument size), so some addresses repeat in the last column. Those slots were identified from `DoMessage` and from the 15 classes that override them.

**Why it happens:**
- MSVC places every overload of a name at the slot of the first one declared, in reverse declaration order.
- `SetSize(cRZPoint const&)` is therefore pulled up to 53 next to `SetSize(int32_t, int32_t)`, which shifts 53–57 and everything from 118 on.
- `GZWinOffset(int32_t, int32_t)` is not declared at all; in the game it is slot 57, which moves all four edges by (dx, dy). So `GZWinMoveTo` moves a window *by* its arguments rather than *to* them. That symptom is visible in any plugin that calls it.

### Right slot, wrong arguments
| method | slot | header | game |
|---|---:|---|---|
| `SetShadeColor(cRZColor const&)` | 111 | passes a pointer | stores the 4-byte argument itself as the colour (`0x0099CA91`: `mov eax,[esp+4]; mov [ecx+0xD0],eax; ret 4`) |
| `AccelerateKeyboardMsg()` | 77 | no argument | pops 1 (`0x0099B980`, `ret 4`) |
| `CheckKeyEquivalent(uint32_t)` | 80 | 1 argument | pops 2 (`0x0099BE94`, `ret 8`) |

These five input handlers are also on the wrong slot (table above), so moving them is not enough:

| method | game slot | header pushes | game pops |
|---|---:|---:|---:|
| `GZOnSetFocus` | 132 | 8 | 4 |
| `GZOnMouseWheel` | 139 | 12 | 16 |
| `GZOnCaptureChanged` | 140 | 16 | 8 |
| `GZOnMouseEnter` | 141 | 8 | 4 |
| `GZOnCommand` | 143 | 4 | 8 |

### When it started
`387a9751` ("Fix the ordering of a few overloads in cIGZWin") wrote the `GetArea`/`GetAreaAbsolute` pairs (47–50) and the fill-colour overloads (102–107) in the game's slot order. Because of MSVC's reverse grouping they now compile backwards. The same probe compiled against `4669fa92` (the version just before it) puts all eight on the game's slots. The rest of the 40 predate it.

### Scope
91 of the 147 declarations were checked against the game: the 40 above are wrong and 51 are right. The other 56 were not decoded, and this report makes no claim about them.

### Evidence
Everything above re-runs against your own exe: https://github.com/Drexel-Macintosh/SimCity4_UI_Modernization/tree/main/tools/sdk/ghidra/verify
- `I-issue-evidence/consolidate_cigzwin.py` produces the table.
- `I-issue-evidence/regression_387a9751.py` shows the regression.
- `A-full-probe/` and `B-second-class-exe-decode/` hold the raw decodes.
