# Known limitations

Every entry below is measured and bounded: what the player sees, what causes
it, and where the boundary sits. The engine reference behind these entries is
in `research/laws/`; the offline regression suite that holds them in place is
in `_tests/`.

## On screen at scaled tiers

- **Vertical art residual on some state strips at 1.5x.** 32 of 193 state
  strips carry an art cell 1-2 px taller than their window at 1.5x, the result
  of a height snap that protects a divide the engine never performs. The
  residual is structurally zero at 2x and 3x.
- **The last item of a flyout sits below the fold at 1.5x.** At 1.5x the
  bottom item of a flyout is outside the visible area when the flyout opens,
  and scrolling to the end leaves empty space below it. The cause is
  container-height and scroll-extent arithmetic rather than art.
- **The Restore-Toolbars button clips at scaled tiers.** The game builds this
  small button with no size of its own — its size comes entirely from its
  four-frame strip — so with scaled art it is born 10 px clipped at 2x. The
  builder, the art, the window id and the position are all decoded.
- **Item icons differ by 2 px between packages at 1.5x.** The item-icon group
  is 68 px tall from one package and 66 px tall from two others at 1.5x: three
  implementations of the icon-dimension rule that agree exactly at 2x and 3x
  and diverge only at the fractional tier. The affected packages rarely place
  adjacent buttons on one toolbar row, which is where a 2 px difference would
  show.

## Performance and lifecycle

- **The first city open of a session is slow with large plugin sets (~54 s).**
  Measured against the same session's second city open (9.2 s): 934 MB in
  1.9 M reads, one core saturated, and a 15-second stretch that does zero
  disk. This is the game's one-time lazy load of the plugin corpus, CPU-bound
  rather than disk-bound; no ini key, hook or call triggers it earlier, and
  prefetching cannot help a load that is not waiting on disk. The one lever
  with a real mechanism — repacking the plugin archives into fewer, larger
  files — would modify another mod's files, so the mod leaves them alone.
- **The process can linger after quitting.** After the game window closes, the
  process sometimes survives with one core pinned. The cause is the game's own
  teardown order: the window manager's valid-window set is destroyed before
  the window tree, so every removal becomes a no-op and one retry loop spins.
  The mod ships a guarded mitigation that releases the loop once the spin is
  measured, plus opt-in per-launch telemetry. The spin is intermittent — two
  runs with byte-identical configuration produced opposite outcomes. Removing
  the cause would mean patching game code, which this mod does not do.

## Coverage boundaries

- **UI size and text size are one knob.** A tier gates the art packages and
  the font table together, so a combination such as UI at 2x with text at 3x
  is not expressible at any layer.
- **The intro video presents at its stock size.** The four geometry sites that
  size it are patched and verified applied; the presentation rect is decided
  downstream of those numbers, so the video keeps its stock size at every
  tier.
- **Some in-world overlays are not scaled.** Zot discs (no-power, no-water,
  no-jobs), the in-world Data Views tint, the underground, subway and pipe
  views, in-world traffic-density colouring, the network drag preview and the
  aircraft landing ring are drawn by the renderer rather than by the window
  layer the mod scales, and they expose no sizing lever.
- **Coverage denominators.** Of 298 script-declared UI roots, 288 are covered
  (96.6%); of 17 code-created named windows, 11 (64.7%); combined 299 of 315,
  94.9%. Windows that are visible but unnameable are deliberately left out of
  the percentage: three creation channels — a singleton factory, computed
  window ids, and art bound by no script — are structurally invisible to any
  offline census.
- **Font line height comes from rendered captures.** The fonts are a format no
  offline tool can read, so line height is measured at 1x and 2x from captures
  of the rendered screen. The chart-legend gate checks its vertical placement
  at those two tiers and records the fractional tiers as skipped.

## Compatibility boundaries

- **Tier minimums bind on height at 3x.** 1.5x requires 1440x1080, 2x requires
  1920x1440, 3x requires 2880x2160. Height is the binding dimension, and the
  Graphics Options dialog — the tallest design panel — is the first element to
  clip when a display falls short.
- **CAM's intro splash art is scaled in the 2x and 3x dialog packages only.**
  The splash art lives in CAM's own archive and appears in no stock extract.
  The 1.5x dialog package leaves it at stock size, so a player running CAM at
  1.5x sees an unscaled splash.
- **Geometry parity, not pixel parity, is the stock-parity bar.** Parity on
  the region screen is verified line-by-line against a true 800x600 reference,
  which fixes positions and extents rather than rendered pixels.
