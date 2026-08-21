# Where SC4 Parents Its Dialogs

SimCity 4's modal confirmations and popups are not children of the 3D city
view. They are parented under the **main window**, so any traversal that starts
at the 3D view — a scaling sweep, an enumeration, a hit-test scope — never sees
them at all.

## Root window ids

- `0xAA921F4F` — "Save and Quit" / "Save and Exit to Region" (three-button
  in-city variant), and also the region-screen "Quit SimCity 4" / "Cancel"
  (two-button, script `I-4a551b4c`, design size 330x109). One id, three stock
  scripts.
- `0x6AAEEC4A` — "Exit to Region" / "Exit and Play City" (three-button).

Other dialogs built the same way include the "Text Entry" prompt used by Save
City (`I-e9263d4c`) and Set Lot Size (`I-e9263de5`).

## They are built in code, not from the .UI script

For these in-city variants the game constructs the dialog through a path that
bypasses the DBPF `.UI` override entirely. A static script override of the root
geometry has no effect on them; they arrive at their 1x design size and must be
adjusted at runtime instead. A guard keyed to each id's own design width
(treat the root as "still 1x" while `w < designW * 1.25`) distinguishes an
untouched dialog from one already resized, and stays correct at fractional
factors where a single flat threshold does not.

The id table and the runtime pass live in `src\UiSpike.cpp` (`kCityDialogIds`).

## They are invisible to Win32 as well

These dialogs are drawn **inside the game's DirectX window**, not as separate
top-level HWNDs. A cover check of the form

```cpp
GetAncestor(WindowFromPoint(pt), GA_ROOT)
```

therefore returns the game's own hwnd whether a dialog is open or not — the
test can never distinguish "pointer is over a dialog button" from "pointer is
over bare terrain". Any input layer that gates on window ancestry will pass
dialog-button taps through to the terrain handler and silently swallow them,
which looks like the dialog ignoring input.

Two consequences follow, and both are worth designing for up front:

1. A component scoped to the 3D view is structurally blind to every dialog and
   popup in the game. Widen the scope to the main window, or accept the gap
   deliberately.
2. Presence of a dialog must be derived from the game's own window tree (root
   id lookup), never from Win32 hit-testing. The OS has no idea these windows
   exist.
