# Test Scenario Axes

A UI scaling fix is not proven by a single run. Most scaling regressions are not
bad code — they are correct code exercised on only one point of a multi-axis
condition space. The axes below are the ones that have actually produced
distinct, reproducible defects; each carries a specific trap that makes a fix
look correct on the axis you tested and wrong on the one you did not.

Regression testing asks "is it still right?". Scenario testing asks "right
under which conditions?". Both are needed.

## 1. Scale tier — 1x / 1.5x / 2x / 3x

1x must be **true stock**: the DLL fully inert, scaled art and the replacement
font stack out of the load path. Setting a scale factor of 1 while leaving
scaled art and font overrides live only *looks* stock and hides the very
differences a 1x reference exists to expose. The screen resolution is part of
the tier — a 1x run at a 4K desktop is not a reference, because every widget is
correct but tiny and formatting becomes the entire question.

**1.5x is where rounding bugs hide, because 2x is exact doubling.** Any integer
division, cell-pitch derivation, or threshold expressed as a fraction of the
scale factor collapses into rounding noise at 1.5x while remaining invisible at
2x and 3x. A fractional-tier metric that does not read exactly 0 at 2x is
measuring itself, not the defect.

Rebuild every tier together. A tier built from a stale generator run is a false
negative on all the other tiers.

## 2. Mod state — full set / one override toggled off / vanilla

Load order decides which copy of a shared UI resource wins. The trap:
**disabling a third-party mod is not enough — the override of that mod must be
moved out too.** Otherwise the local copy keeps the mod's layout alive, and the
"vanilla" control is silently still modded. Toggling scripts should move both
halves as one operation.

Plugin scanning is recursive, so a stash placed *inside* the plugins tree
disables nothing. Enumerate both the user and application plugin trees before
believing any claim that a run was stock.

## 3. Game mode — region / mayor / god pre-founding / god founded

God mode before a city is founded and god mode after founding present different
toolbars and different vertical pitch; a layout rule verified in one is not
verified in the other. Never gate behaviour on a state test that has not been
checked in every city state, and re-derive notes after founding a city, since
measurements taken pre-founding do not carry over.

## 4. Panel lifecycle

Distinct states, each capable of its own defect:

- city load while the panel is hidden
- **first open per city load** — the game binds geometry, images, and crops once
  at this moment
- re-open within the same session
- compact versus expanded form
- after a city switch — **windows are reused across cities**, so stale bind-time
  state survives
- region ↔ city transitions

First-open bugs survive testing precisely because re-open works. A defect that
appears only on first use is an uninitialised latch, and a latched crop bound at
first show never refreshes on later resizes.

## 5. Render mode

DirectX fullscreen renders at **monitor native resolution — the requested size
is ignored**. Windowed and software rendering honour the request. A wrapper
layer can also override a windowed-mode request on its own, so setting windowed
mode in the game's own configuration alone does nothing; the wrapper's
fullscreen setting has to change with it.

## 6. Input path — mouse / touch layer / synthesized clicks

The game **polls the physical cursor position for drags** and ignores posted
messages. Synthesized click injection therefore validates hit-testing but not
drag behaviour; drag paths must be exercised with a real pointer.

## Environment notes

- The game process runs elevated and holds the DLL and archives open. Deploys
  must wait for it to close rather than attempting to terminate it.
- `LiveDumpMs` produces large logs — on the order of 12 MB per session when
  left enabled — and only takes effect at process start. The `[Probe]` settings
  are live-tunable during a run.
- The directional probe needs its band limit raised (`BandL=900`) or the news
  ticker floods the capture.
