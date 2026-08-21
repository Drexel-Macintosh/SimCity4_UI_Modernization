# Deploying to a Running Game

SimCity 4 runs elevated and holds `SC4UIScale.dll` and the tier `.dat` packages
open for the whole session. A new build therefore cannot be copied over a live
install, and the process must not be killed to force the issue: terminating it
discards the player's unsaved city state and destroys the session log that
verification depends on. Deployment waits for the game to exit instead.

## Wait-for-close deployment

`_tests\Deploy-OnGameClose.ps1` polls for the `SimCity 4` process every 5
seconds and does nothing until it exits. Once the process is gone it copies the
freshly built DLL and every tier-managed package into the Plugins tree, then
asserts that the deployed DLL's byte size matches the build output and fails
with a non-zero exit code if it does not.

Run the watcher in the background with a lifetime long enough for a real play
session — a five-minute window is far too short, and a watcher that times out
mid-session leaves the install on the previous build while the console reports
nothing wrong.

Two details of the wait loop matter:

- The game frequently **hangs on shutdown**: the window closes but the process
  does not exit, and a silent poll loop is then indistinguishable from "still
  playing". The watcher nags once a minute with the process id and the elapsed
  wait so the operator can end the orphaned process deliberately. It still never
  kills the process itself — a half-written `.dat` is the worse failure.
- `SC4UIScale.log` in the Plugins folder is **recreated from scratch on every
  game launch**, and every deploy is immediately followed by a launch. The
  moment just after the process exits is the last safe point to preserve the
  previous run's log, so the watcher copies it aside, named by the log's own
  modification time rather than the current clock, before touching anything
  else.

The working order is: build, start the watcher, announce the build is ready,
let the player close the game when they choose, then confirm the
`deployed ... at HH:MM:SS` line before treating anything as shipped.

## The boot matrix is not a routine check

`_tests\Test-BootMatrix.ps1` deliberately violates the rule above: it is a live
regression that **launches and kills the game once per matrix entry** and
rewrites `SC4GraphicsOptions.ini` between entries, walking 800x600 (stock tier),
1920x1080 and 1600x1200 (1.5x), and 2400x1600 (2x), deleting the log before each
boot. It restores the native resolution only if it runs to completion. Interrupt
it and it leaves the graphics ini at whatever resolution it was mid-way through
and a game process running; the recovery is to restore `WindowWidth` and
`WindowHeight` to the machine's native values by hand.

Never launch it as part of a general "run the suites" pass, and never while
someone may be playing. It takes roughly ten minutes.

## The routine suites are offline

Verifying a build does not require the game to be open. `Test-DatIntegrity`,
`Test-ScaleTierDecide`, `Test-UiMapDiff` and the offline UI-map drivers under
`tools\uimap\emu\` all run against files on disk and are the correct default
regression pass. Reserve live-boot checks for questions that genuinely cannot be
answered from the shipped artifacts.
