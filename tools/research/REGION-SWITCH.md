# REGION-SWITCH: why the population number lands outside the bar after a live region switch

Investigation of the region info panel (0x09EBE9EE) misplacement that appears only after a
mid-session Load Region switch, never on a fresh boot.

**TL;DR** - On a live switch the game destroys and rebuilds the ENTIRE region UI within one
250ms tick. All nine whitelisted panel roots come back at new addresses and classify Fresh
(correct), but 2-3 of 0x09EBE9EE's descendants land on recycled heap addresses that still
carry scaleMap records from the destroyed windows. Those descendants are anonymous
(id=0x00000000), so Classify's id check cannot evict the stale record; the size check then
matches neither `orig` nor `scaled` and the window classifies **Unrecognized - permanently
skipped**, left at 1x design geometry inside the 2x panel. The fix is a targeted purge:
when a whitelisted panel root classifies Fresh, erase the scaleMap records of every pointer
in its CURRENT subtree before sweeping it - which makes a switch bookkeeping-identical to a
fresh boot.

---

## Evidence base

| File | Version | Content |
|---|---|---|
| `...\Plugins\SC4TouchControls.log.bak-dialogtest` | v2.5.5-dialogs (header line 1) | **The switch session.** Boot at region 22:05:58, FOUR live region switches (22:10:21, 22:11:00, 22:11:10, 22:12:15), city entry 22:12:18, ends 22:13:23. |
| `...\Plugins\SC4TouchControls.log.bak-userclickthrough` | v2.5.3-interior | Earlier session; ONE region activation (21:29:00), no switches. Contains the old dialog position-compounding bug (342 -> 684 -> 1368), already fixed by `origL/origT`. |
| `...\Plugins\SC4TouchControls.log` (live) | v2.5.7-overhang | Fresh-boot proof session (22:30:05 region up, 9/9 scaled, exit 22:32:08). This is the session behind `tools\capture\out\region-v257-fairview.png`. |
| `src\UiSpike.cpp` / `src\UiSpike.h` | current | Classify / ScalePanelsUnder / ScalePanelRoot / ScaleSubtree / RegionWatchTick as analyzed. |

Note: the task brief said the switch session was v2.5.6; no v2.5.6 log exists in Plugins.
The dialogtest backup (v2.5.5-dialogs) is the log containing the live switches and matches
the described scenario (repeated Load Region use, ending with a city entry).

Logging caveat ruled out: `logLevel=2` = `LogLevel::Debug` (Logger.h enum), and Debug-level
lines demonstrably appear (every `region panel ... windows scaled` line is Debug). So the
ABSENCE of tombstone lines, guard lines, and catch-up passes below is real evidence, not
suppressed output.

---

## 1. What exactly happens at a live switch

### Host presence: no re-stabilization, ever

`UiSpike: region screen up` appears **exactly once** in the dialogtest session (22:05:58.328)
and never again through four switches. Therefore `RegionWatchTick`'s `present` never went
false on any 250ms tick: `regionActive` stayed true and the stability gate
(`regionChildCountSeen` / `regionStableTicks`) never re-ran. Either the host 0xEA659793
survives the switch, or it is destroyed and recreated entirely inside one tick window - the
log cannot distinguish (the host is re-found by ID each tick via
`GetChildWindowFromIDRecursive`), but for the watcher's behavior it does not matter: **the
per-tick region pass runs straight through the switch with no settle delay**, and each
switch was fully processed in a single pass at most 250ms after the rebuild.

### The rebuild is total, and the pass sees it atomically

At each switch timestamp, ALL NINE whitelisted panels log a full re-scale **from design
geometry** (`(5,1496 415x106)` etc.) with **no `[re-scaled after reset]` suffix**. In
`ScalePanelRoot` the suffix-less line means `state == Fresh`, i.e. the pointer was not in
scaleMap (or was evicted by id mismatch). Since every root has a distinctive id, Fresh here
means **new window objects**: the game rebuilds the whole region screen wholesale on a
region switch (it does NOT keep windows and merely update text - that hypothesis is dead).

There are **zero** `[re-scaled after reset]` lines for any region panel in the entire
session. The only such lines anywhere are city-side (`0xC99237A0` at 22:13:23) and the
v2.5.3 dialog-walk lines in the userclickthrough log.

Each switch pass is one tick: all nine panel lines share the same or adjacent millisecond,
in the host's stable EnumChildren order:

```
0x0BB0F5E7, 0x6BB92BCA, 0x09EBE9EE, 0x6A91DC15, 0x6A91DC16,
0x09EBEE45, 0x09EBEE60, 0xEA8CAD19, 0x6A91DC14
```

Timeline of the four switches (each preceded by the user opening the Load Region dialog):

| Load Region dialog scaled+docked | Switch pass (all 9 panels Fresh) | Gap |
|---|---|---|
| 22:10:17.039 | 22:10:21.678 | 4.6s |
| 22:10:51.047 | 22:11:00.532 | 9.5s |
| 22:11:05.809 | 22:11:10.743 | 4.9s |
| 22:12:09.949 | 22:12:15.133 | 5.2s |

City entry follows at 22:12:18.264 (`City view acquired`).

### The smoking gun: scaled-window counts per panel, boot vs switches

`region panel 0x… - N windows scaled` (N = root + descendants newly mutated that pass):

| Panel | subtree size | boot 22:05:58 | sw1 22:10:21 | sw2 22:11:00 | sw3 22:11:10 | sw4 22:12:15 | descendant ids |
|---|---|---|---|---|---|---|---|
| 0x0BB0F5E7 (legend) | 10 | 10 | 10 | 10 | 10 | 10 | all unique |
| 0x6BB92BCA (mini btn) | 2 | 2 | 2 | 2 | 2 | 2 | unique |
| **0x09EBE9EE (info bar)** | **9** | **9** | **7** | **6** | **6** | **6** | **6 of 8 are id=0** |
| 0x6A91DC15 | 3 | 3 | 3 | 3 | 3 | 3 | 0xAAAA + unique |
| 0x6A91DC16 | 5 | 5 | 5 | 5 | 5 | 5 | 0xAAAA + unique |
| 0x09EBEE45 (top flyout) | 18 | 18 | 18 | 17 | 17 | 18 | several id=0, similar sizes |
| 0x09EBEE60 (opts flyout) | 10 | 10 | 10 | 10 | 8 | 9 | several id=0 |
| 0xEA8CAD19 | 3 | 3 | 3 | 3 | 3 | 3 | 0xAAAA + unique |
| 0x6A91DC14 (top bar) | 3 | 3 | 2 | 3 | 3 | 3 | 0xAAAA + one id=0 |

The correlation is exact:

- Panels whose descendants all carry **unique ids** re-scale at full count on every switch.
  (Classify's `GetID() != rec.id` eviction turns any address reuse into Fresh.)
- Panels containing **id=0x00000000** descendants drop 1-3 windows per switch, stochastically.
- The **0x0000AAAA** placeholders never drop despite being non-unique - because every AAAA
  window is 20x20, so a cross-collision still matches `rec.origW/H` and lands
  `ResetToOriginal` (re-scaled, counted). Uniform size makes them collision-proof.
- 0x09EBEE45's id-0 windows cluster around a few sizes (150-162x21, 193x74 pairs), so a
  recycled address often holds a same-size record -> ResetToOriginal -> re-scaled; it drops
  only occasionally. 0x09EBE9EE's id-0 windows are ALL different sizes (20x20, 112x18,
  111x20, 384x26, 408x102), so a cross-collision almost never matches -> it loses 2-3
  windows on EVERY switch. Rot probability tracks size diversity, exactly as the
  address-roulette model predicts.

Why cross-collisions are common at all: the recycled resource is the **window object
allocation** (cGZWin-sized heap block), not anything related to on-screen size. All ~68
destroyed region windows free into the same size-class pool and the rebuilt windows
reallocate from it (LIFO) - so a new window lands on SOME dead window's address with high
probability, and only the window's GZ id decides whether the stale record gets evicted.

### The skipped windows are skipped forever

Between and after the switch passes there are **no** further `region panel 0x09EBE9EE - N`
lines until the next switch (an all-AlreadyScaled pass logs nothing, n=0). If the missing
descendants had been created late (after the pass), a subsequent tick would have classified
them Fresh and logged a small-count line - never happens. If the game had been resetting
them after our pass, we would see per-tick ResetToOriginal churn and, after 4 rounds, the
Info-level `tombstoned (game-managed geometry)` line - **zero tombstone lines in the whole
session**. If the double-scale guard had refused them, the guard lines (Info for roots,
Debug for subtree windows - and Debug is on) would appear - **zero guard lines**.

Conclusion: the skipped descendants were present during the switch pass and classified
**Unrecognized** every tick from then on. Unrecognized is not a tombstone - it is re-derived
each tick from the stale record - but it is equally permanent while the foreign record
occupies that address. That is precisely why the continuous 250ms pass never healed it.

### The 0x09EBE9EE subtree, and where the number visibly goes

Design (1x) vs correctly scaled (2x) geometry, from the region and BOOT dumps:

| Window | id | design | scaled (boot-proven) |
|---|---|---|---|
| info-bar panel root | 0x09EBE9EE | (5,1496) 415x106 | (10,1388) 830x212 |
| hidden marker | 0x00000000 | (0,84) 20x20 | (0,168) 40x40 |
| **population wrapper** | **0x00000000** | **(39,37) 112x18** | **(78,74) 224x36** |
| population label | 0xC9E41918 | (0,0) 112x18 | (0,0) 224x36 |
| city-count wrapper | 0x00000000 | (47,11) 111x20 | (94,22) 222x40 |
| city-count inner | 0x00000000 | (0,0) 111x20 | (0,0) 222x40 |
| region-name wrapper | 0x00000000 | (17,68) 384x26 | (34,136) 768x52 |
| region-name label | 0xEA5BD179 | (0,0) 384x26 | (0,0) 768x52 |
| bar background art | 0x00000000 | (5,-3) 408x102 | (10,-6) 816x204 |

The user-visible symptom maps to the **population wrapper losing the roulette while the
population label wins it**: the wrapper (id 0) hits a stale record -> Unrecognized -> stays
at design (39,37) 112x18; the label inside it (unique id 0xC9E41918) evicts whatever record
its address held -> Fresh -> scaled to 224x36. Result: a double-sized population number
anchored at panel-relative (39,37) instead of (78,74) - absolute (49,1425) instead of
(88,1462) - i.e. shifted 39px left and 37px up, overflowing its 112x18 wrapper, drawn at
the panel's top-left ABOVE the engraved number line of the (correctly doubled) bar art.
That matches the screenshot (number top-left, outside the bar band). The inverse roulette
(wrapper scaled, label skipped) would give a correctly-placed but half-sized number - not
what was seen. The pop-0 vs 1.26M text change is irrelevant to geometry: the wrapper is a
fixed 112x18 in the .UI design regardless of caption (both dumps confirm).

The same rot is visible, independently of region switches, in the Load Region dialog
itself: its recreated-per-open subtree logs 8, 7, 7, 7, 7, 6, 6, 7, 8, 8, 8, 6, 8
descendants across the session's reopenings - id-0 dialog children rolling the same dice
against the accumulating stale-record pool.

---

## 2. Hypotheses, ranked

**(1) PRIMARY - stale anonymous-id records block re-scale of recreated children
("partial recreation", task's hypothesis b, with the blocker identified).**
The panel does NOT persist - everything is recreated - but 2-3 recreated id-0 descendants
land on recycled addresses whose scaleMap records belonged to different (destroyed) windows.
`Classify` cannot evict (`0 == 0` id match), the size matches neither `origW/H` nor
`scaledW/H`, and the window classifies Unrecognized - by design "leave alone", by effect
"never scale". Grounded in: the count table above (drops only in id-0-bearing subtrees, on
every switch, permanent); absence of tombstone/guard/catch-up lines with Debug logging
proven active; the AAAA-uniform-size and 0x09EBEE45-size-cluster corroborations; the
dialog-descendant-count rot showing the identical mechanism elsewhere.

**(2) REFUTED - game re-lays the pop text at design coords after our re-scale
(task's hypothesis a).** That path requires either per-tick ResetToOriginal churn
(`region panel ... windows scaled` lines between switches - none), a tug-of-war tombstone
after >3 rounds (`tombstoned (game-managed geometry)` - none in the session), or an
Unrecognized produced by a game-side resize - but then the boot session would eventually
show the same relayout and the fresh-boot proof would break. Boot is clean, switch is
instantly broken in the same pass: it is a classification failure, not a layout fight.

**(3) REFUTED - tombstone carried over from an earlier tug-of-war.** scaleMap is
process-local (no cross-session persistence), and this session contains zero tombstone
lines. The v2.5.3 dialog-walk (userclickthrough) predates the `origL/origT` fix and left no
in-process residue relevant here.

**(4) REFUTED - double-scale guard refusal.** Both guard messages (Info panel-level, Debug
subtree-level) are absent; Debug is on.

**(5) Unobserved variant, same root cause - late-created children.** If the game ever
creates a region child a tick after the rebuild, it classifies Fresh at a fresh address
(fine) or collides with a stale record (same rot). The logs show all switch scaling
completed in single passes, so this variant did not occur here, but the fix below should
keep it in mind (see edge case).

---

## 3. Recommended fix: purge-on-Fresh-root (make a switch look like a boot)

### Core change

A Fresh classification of a **whitelisted panel root** proves the game just (re)built that
subtree: the root is a new object, therefore every descendant is also a new object, and any
scaleMap record found at a descendant's address is stale by construction (its owner was
destroyed; the address was recycled). Erasing exactly those records cannot touch any live
window's record - we only erase pointers that exist in the NEW subtree - and it restores the
boot invariant (no records for the subtree) so every child classifies Fresh and the very
same pass scales 9/9, just like the proven-good fresh boot.

Sketch (UiSpike model, proven-safe calls only - EnumChildren + map erase, no mutation):

```cpp
// UiSpike.h (private)
void PurgeDescendantRecords(class cIGZWin* win, int depth);

// UiSpike.cpp
void UiSpike::PurgeDescendantRecords(cIGZWin* win, int depth)
{
    if (!win || depth > kMaxDepth) { return; }
    ChildSnapshot snap = {};
    win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
    for (int i = 0; i < snap.count; i++)
    {
        scaleMap.erase(snap.wins[i]); // stale by construction under a Fresh root
        PurgeDescendantRecords(snap.wins[i], depth + 1);
    }
}
```

Call site - `ScalePanelRoot`, immediately after the single `Classify(win)`:

```cpp
const ScaleState state = Classify(win);
if (state == ScaleState::Fresh)
{
    // Rebuilt (or first-seen) subtree: drop stale records at recycled
    // descendant addresses so the sweep scales them as Fresh - a live
    // region switch becomes bookkeeping-identical to a fresh boot.
    PurgeDescendantRecords(win, 0);
}
```

Do not re-Classify for this (Classify has side effects: id-eviction and the tug-of-war
counter); branch off the one existing call. On the true first boot the purge is a no-op
(nothing recorded yet), so behavior there is unchanged.

### Scope

- **Region pass**: required - this is the proven bug.
- **DialogDockTick** (`state == Fresh` branch, before its child sweep): recommended - the
  8/7/6 descendant-count rot shows dialog interiors suffer identically. Currently gated
  behind `DockDialogs=1`, so zero shipping risk.
- **City pass**: the invariant (Fresh root implies new descendants) is structural, not
  region-specific, and the same call site covers it automatically. City HUD panels that
  persist across city loads classify AlreadyScaled and are never purged, so the documented
  double-scale hazard is untouched. If minimal blast radius is preferred for the first
  build, gate the purge on `isRegionPass` (thread a flag into ScalePanelRoot) and widen it
  after the region validation passes.

### Why not the alternatives

- **Clearing scaleMap on region re-activation**: too blunt - region records coexist with
  live city/dialog records in one map, and global clears are the canonical 2x->4x hazard.
- **Re-arming the stability gate on switch**: does nothing for this bug (the pass already
  ran AFTER the rebuild was complete - classification, not timing, failed) and the log
  shows rebuilds are tick-atomic. Not needed.
- **Watching the region-name text for changes**: no proven-safe caption getter exists on
  this binary, text changes do not move geometry anyway, and the Fresh root is a strictly
  more reliable rebuild signal that requires no new vtable calls.
- **Relaxing Classify for id==0 records (evict on any size mismatch)**: would also fix this
  but weakens the Unrecognized protection everywhere (a game-resized anonymous window would
  get re-scaled). Hold in reserve for the one edge case purge cannot cover: a child created
  AFTER the purge pass at a recycled foreign address (not observed in any log to date).

### Validation checklist

1. Rebuild, boot to region: expect the unchanged boot signature
   (`region panel 0x09EBE9EE - 9 windows scaled`) and a clean capture (parity with
   `region-v257-fairview.png`).
2. Perform 3-4 live switches including a pop-0 -> 1.26M pair (Kanto Tokai -> Fairview):
   every switch pass must now log **full boot-equal counts** for all nine panels
   (0x09EBE9EE = 9, 0x6A91DC14 = 3, 0x09EBEE45 = 18, 0x09EBEE60 = 10) - the count table in
   section 1 is the regression oracle; any N below the boot value means a descendant was
   skipped again.
3. Verify the population number sits in the bar band after each switch (capture at
   (88,1462) expected for the label origin).
4. With `DockDialogs=1`, reopen Load Region 5+ times: descendant count should stabilize at
   the full value (8) instead of wandering 8/7/6.
5. Enter a city afterwards and confirm the city HUD scale-up still logs its usual counts
   (no double-scale guard lines) - guards remain as backstop.
