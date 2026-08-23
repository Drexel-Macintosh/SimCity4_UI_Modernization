# Law: Never shift the strip child window independently of the container

**Date:** 2026-08-22
**Status:** ACTIVE
**Scope:** Sub-flyout 0x8A6E61E0 (shared second-level menu); applies to all
flyout families with bar+strip architecture.

## The rule

Never move the strip child window (`0x8A2CAD8B`) independently of its parent
container (`0x8A6E61E0`). The strip and bar art are a single layout unit
computed by the builder (`sub_7EAEB0`); moving one without the other breaks
visual alignment.

## What happened

### Attempt: StripShiftRows (v4.0.27 – v4.0.29, retired v4.0.30)

The ring arm meets row 3 ("Marina") at 2x instead of row 7 ("Tourist Trap")
in stock. StripShiftRows was introduced to shift the strip child window up
inside the container so the arm would meet the correct row.

**What was tried:**
1. Strip window `GZWinMoveTo(0, delta)` per sweep tick — shifted icons up
2. Bar art `bgShiftY` offset in `DrawBarScaled` — tried to make bar follow
3. Top-cap clip guard (`s[1] > 0`) — tried to fix top clipping
4. Born-path `gSubShiftContWin` capture — tried to fix first-frame timing

**Every variant failed.** The fundamental problem: the bar art is painted into
the **container's buffer** at builder-computed positions (top cap at y=0,
spine, bottom cap at y=contentH). The strip is a **child window** with its
own coordinate space. Shifting the strip moves the icons but not the bar.

### Why every fix attempt failed

| Attempt | Result |
|---|---|
| `bgShiftY = gBarShiftY` (shift bar with strip) | Bar top cap clipped at y<0; bar became shorter, leaving top icons on dark background |
| `bgShiftY` only for `s[1]>0` (skip top cap) | Spine clipped at top, bottom cap shifted up — bar still too short |
| `bgShiftY = 0` (don't shift bar) | Bar covers full height but icons are offset from bar center — visual misalignment |
| Born-path `gSubShiftContWin` | Fixed first-frame timing but didn't solve the fundamental bar/strip split |

### The architecture lesson

The sub-flyout has **two independent drawing layers**:
1. **Container buffer** — bar art (pill) + ring, painted by the game's
   `Plot()` function into `[0xdc]`, stretched to window size
2. **Strip child window** — icon pictures, painted by the strip's own
   `Plot()` into its own buffer, composited on top

These layers share the container's coordinate space but are drawn
independently. The bar covers the full container height by construction
(builder: `contentH = max(stripH, [0xF4]) + 2*[0xE8]`). The strip is
centered inside it (`stripTop = (contentH − stripH) >> 1`).

Moving the strip without moving the bar desynchronizes two layers that
the game expects to be in their builder-computed positions.

### How other flyouts stay aligned

Every working flyout family (mayor, god tools, first-level) keeps the
strip and bar in their builder positions:
- **Mayor flyouts** (`0x699306ED` etc.): `ScaleSubtree` scales everything
  together; `GZWinMoveTo` on the container moves all children as a unit
- **First-level flyouts** (twin `sub_7E7270`): `SubPlaceDetour` scales the
  container `SetW/SetH` and the strip rect `[0x108]` together; the container
  dock carries both
- **Disaster flyout**: bar shift (`gBarShiftY`) works because the disaster
  strip is NOT a child window — both bar and strip are painted into the same
  container buffer

The sub-flyout is the **only** family where someone attempted an independent
strip shift. It is also the only family where bar+strip alignment broke.

## What to do instead

To fix the ring arm meeting the wrong row, adjust the ring's Y position
within the container via `gSubRingAutoY`, not the strip position. The ring
is drawn by our code at `d[1] + SubRingDYEff() + gSubRingAutoY` and has
full independent control. Moving the ring down makes the arm meet a lower
row; moving it up makes it meet a higher row. This keeps the strip and bar
in their builder-computed, mutually-aligned positions.

## Related laws

- `project-sc4-flyout-never-prescroll.md` — scroll is never the fix either
- `GOD-MODE-FLYOUTS.md` — container Plot pipeline, bar tile anatomy
- `SUBFLYOUT-BUILDER.md` — builder constants, `Place()` formula, strip centering
