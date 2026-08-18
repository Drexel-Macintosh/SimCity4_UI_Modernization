---
name: reference-sc4-dialogs-live-under-main-window
description: "SC4's modal confirms and popups are parented under the MAIN WINDOW, not the 3D view - which is why SC4TouchControls (which only holds view3d) is structurally blind to them and its tap gate swallows their buttons. Root ids 0xAA921F4F / 0x6AAEEC4A."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 12c17599-6d28-4c98-99ab-fc651db4fa8f
  modified: 2026-08-14T16:09:17.759Z
---

**SC4's dialogs are NOT under the 3D view.** The in-city quit / exit-to-region
confirmation dialogs are modal popups **parented under the MAIN WINDOW**, and
the city pass over the 3D view never sees them. Root ids:

- `0xAA921F4F` — "Save and Quit" / "Save and Exit to Region" (3-btn), AND the
  region-screen "Quit SimCity 4"/"Cancel" (2-btn, script I-4a551b4c)
- `0x6AAEEC4A` — "Exit to Region" / "Exit and Play City" (3-btn)

Source of truth: `SC4UIScale\src\UiSpike.cpp` ~13026 and the `kCityDialogIds`
table (~13335, `modalConfirm`). Those are the GAME's window ids, so they are
valid facts about SC4 itself, not about that mod — safe to use from
[[project-sc4-touch-controls]] without violating the
[[project-sc4-projects-split-and-entry-point]] zero-shared-files rule. Port the
FACTS, never the code.

⛔ **WHY THIS BITES TOUCH.** `SC4TouchControls` only ever holds `view3d`, so it
is **structurally blind to every dialog and popup**. It cannot see them by
Win32 either: they are drawn INSIDE the game's DirectX window, so the
`GetAncestor(WindowFromPoint(...), GA_ROOT)` cover-check returns the game hwnd
itself (device log 2026-08-13: every cover-check logged `cover == hwnd`). The
old "the game's own save/quit dialogs are separate HWNDs" comment in
`TouchInputHandler.cpp` is therefore WRONG for the in-city case.

Consequence: the plop gate treats dialog buttons as bare terrain and swallows
the taps (`plop tap silent`), which is why quit-without-save needed ESC
mashing. See [[project-sc4-touch-controls]].
