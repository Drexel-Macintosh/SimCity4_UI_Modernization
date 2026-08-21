# REGION-SWITCH: why the population number lands outside the bar after a live region switch

Reference for the region info panel (0x09EBE9EE) misplacement that appears only after a
mid-session Load Region switch, never on a fresh boot.

**TL;DR** - On a live switch the game destroys and rebuilds the ENTIRE region UI within one
250ms tick. All nine whitelisted panel roots come back at new addresses and classify Fresh
(correct), but 2-3 of 0x09EBE9EE's descendants land on recycled heap addresses that still
carry scaleMap records from the destroyed windows. Those descendants are anonymous
(id=0x00000000), so Classify's id check cannot evict the stale record; the size check then
matches neither `orig` nor `scaled` and the window classifies **Unrecognized - permanently
skipped**, left at 1x design geometry inside the 2x panel. The cure is a targeted purge:
when a whitelisted panel root classifies Fresh, erase the scaleMap records of every pointer
in its CURRENT subtree before sweeping it - which makes a switch bookkeeping-identical to a
fresh boot.

The code behind every claim below is `src\UiSpike.cpp` / `src\UiSpike.h`: `Classify`,
`ScalePanelsUnder`, `ScalePanelRoot`, `ScaleSubtree`, `RegionWatchTick`,
`PurgeSubtreeRecords`.

Logging caveat ruled out: `logLevel=2` is `LogLevel::Debug` (the `Logger.h` enum), and
Debug-level lines demonstrably appear (every `region panel ... windows scaled` line is
Debug). So the ABSENCE of tombstone lines, guard lines, and catch-up passes below is real
evidence, not suppressed output.

---

## 1. What exactly happens at a live switch

### Host presence: no re-stabilization, ever

`UiSpike: region screen up` appears **exactly once** per process run and never again through
a series of switches. `RegionWatchTick`'s `present` therefore never goes false on any 250ms
tick: `regionActive` stays true and the stability gate (`regionChildCountSeen` /
`regionStableTicks`) never re-runs. Either the host 0xEA659793 survives the switch, or it is
destroyed and recreated entirely inside one tick window - the log cannot distinguish (the
host is re-found by ID each tick via `GetChildWindowFromIDRecursive`), and for the watcher's
behavior it does not matter: **the per-tick region pass runs straight through the switch
with no settle delay**, and each switch is fully processed in a single pass at most 250ms
after the rebuild.

### The rebuild is total, and the pass sees it atomically

At each switch, ALL NINE whitelisted panels log a full re-scale **from design geometry**
(`(5,1496 415x106)` etc.) with **no `[re-scaled after reset]` suffix**. In `ScalePanelRoot`
the suffix-less line means `state == Fresh`, i.e. the pointer was not in scaleMap (or was
evicted by id mismatch). Since every root has a distinctive id, Fresh here means **new
window objects**: the game rebuilds the whole region screen wholesale on a region switch; it
does not keep windows and merely update text. There are **zero** `[re-scaled after reset]`
lines for any region panel; the only such lines are city-side (`0xC99237A0`).

Each switch pass is one tick: all nine panel lines share the same or adjacent millisecond,
in the host's stable EnumChildren order:

```
0x0BB0F5E7, 0x6BB92BCA, 0x09EBE9EE, 0x6A91DC15, 0x6A91DC16,
0x09EBEE45, 0x09EBEE60, 0xEA8CAD19, 0x6A91DC14
```

Each switch is preceded by the player opening the Load Region dialog, which scales and docks
several seconds before the switch pass fires.

### The smoking gun: scaled-window counts per panel, boot vs switches

`region panel 0x… - N windows scaled` (N = root + descendants newly mutated that pass), for
a boot followed by four live switches:

| Panel | subtree size | boot | switch 1 | switch 2 | switch 3 | switch 4 | descendant ids |
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
- Panels containing **id=0x00000000** descendants drop 1-3 windows per switch,
  stochastically.
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
lines until the next switch (an all-AlreadyScaled pass logs nothing, n=0). Had the missing
descendants been created late (after the pass), a subsequent tick would have classified them
Fresh and logged a small-count line - that line never appears. Had the game been resetting
them after the pass, the log would carry per-tick ResetToOriginal churn and, after 4 rounds,
the Info-level `tombstoned (game-managed geometry)` line - **zero tombstone lines**. Had the
double-scale guard refused them, the guard lines (Info for roots, Debug for subtree windows
- and Debug is on) would appear - **zero guard lines**.

Conclusion: the skipped descendants are present during the switch pass and classify
**Unrecognized** every tick from then on. Unrecognized is not a tombstone - it is re-derived
each tick from the stale record - but it is equally permanent while the foreign record
occupies that address. That is precisely why the continuous 250ms pass never heals it.

### The 0x09EBE9EE subtree, and where the number visibly goes

Design (1x) vs correctly scaled (2x) geometry:

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

The player-visible symptom maps to the **population wrapper losing the roulette while the
population label wins it**: the wrapper (id 0) hits a stale record -> Unrecognized -> stays
at design (39,37) 112x18; the label inside it (unique id 0xC9E41918) evicts whatever record
its address held -> Fresh -> scaled to 224x36. Result: a double-sized population number
anchored at panel-relative (39,37) instead of (78,74) - absolute (49,1425) instead of
(88,1462) - i.e. shifted 39px left and 37px up, overflowing its 112x18 wrapper, drawn at
the panel's top-left ABOVE the engraved number line of the (correctly doubled) bar art. That
is the observed placement: the number sits top-left, outside the bar band. The inverse
roulette (wrapper scaled, label skipped) would give a correctly-placed but half-sized number,
which is not what the panel shows. A caption change such as pop-0 to 1.26M is irrelevant to
geometry: the wrapper is a fixed 112x18 in the .UI design regardless of caption.

The same rot is visible, independently of region switches, in the Load Region dialog itself:
its recreated-per-open subtree logs 8, 7, 7, 7, 7, 6, 6, 7, 8, 8, 8, 6, 8 descendants across
repeated reopenings - id-0 dialog children rolling the same dice against the accumulating
stale-record pool.

---

## 2. The mechanism

**Stale anonymous-id records block re-scale of recreated children.** The panel does NOT
persist - everything is recreated - but 2-3 recreated id-0 descendants land on recycled
addresses whose scaleMap records belonged to different (destroyed) windows. `Classify`
cannot evict (`0 == 0` id match), the size matches neither `origW/H` nor `scaledW/H`, and
the window classifies Unrecognized - by design "leave alone", by effect "never scale".
Grounded in: the count table above (drops only in id-0-bearing subtrees, on every switch,
permanent); absence of tombstone/guard/catch-up lines with Debug logging proven active; the
AAAA-uniform-size and 0x09EBEE45-size-cluster corroborations; the dialog-descendant-count
rot showing the identical mechanism elsewhere.

The alternatives are excluded, each by a measured null: a game-side re-lay of the pop text
would need per-tick ResetToOriginal churn or a tug-of-war tombstone (zero of either, and a
clean boot proves the relayout never happens); a carried-over tombstone is impossible because
scaleMap is process-local with zero tombstone lines; and a double-scale-guard refusal is
ruled out because both guard messages (Info panel-level, Debug subtree-level) are absent with
Debug on.

**Edge case, same root cause - late-created children.** If the game creates a region child a
tick after the rebuild, it classifies Fresh at a fresh address (fine) or collides with a
stale record (same rot). All switch scaling completes in single passes, so this variant does
not arise in practice; the cure in section 3 accounts for it.

---

## 3. The cure: purge-on-Fresh-root (make a switch look like a boot)

`PurgeSubtreeRecords` in `src\UiSpike.cpp`, called on a Fresh panel root and again on Fresh
by the dialog paths. The mechanism:

A Fresh classification of a **whitelisted panel root** proves the game just (re)built that
subtree: the root is a new object, therefore every descendant is also a new object, and any
scaleMap record found at a descendant's address is stale by construction (its owner was
destroyed; the address was recycled). Erasing exactly those records cannot touch any live
window's record - only pointers that exist in the NEW subtree are erased - and it restores
the boot invariant (no records for the subtree) so every child classifies Fresh and the very
same pass scales 9/9, just like the proven-good fresh boot.

The walk uses proven-safe calls only - EnumChildren plus map erase, no mutation - and warns
once per epoch if the depth cap truncates it, because a silent stop leaves stale records
below the cap that read as "already scaled" on the next sweep:

```cpp
// UiSpike.h (private)
void PurgeSubtreeRecords(class cIGZWin* win, int depth);

// UiSpike.cpp
void UiSpike::PurgeSubtreeRecords(cIGZWin* win, int depth)
{
    if (win && depth > kMaxDepth)
    {
        static int purgeWarnEpoch = -1;
        if (purgeWarnEpoch != gGaugeEpoch)
        {
            purgeWarnEpoch = gGaugeEpoch;
            Logger::Get().WriteLine(LogLevel::Info,
                "UiSpike: PurgeSubtreeRecords DEPTH CAP %d reached under "
                "id=0x%08X - records below it are NOT purged",
                kMaxDepth, win->GetID());
        }
    }
    if (!win || depth > kMaxDepth) { return; }

    ChildSnapshot snap = {};
    win->EnumChildren(GZIID_cIGZWin, ChildSnapshot::Callback, &snap);
    for (int i = 0; i < snap.count; i++)
    {
        scaleMap.erase(snap.wins[i]); // stale by construction under a Fresh root
        PurgeSubtreeRecords(snap.wins[i], depth + 1);
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
    PurgeSubtreeRecords(win, 0);
}
```

Do not re-Classify for this (Classify has side effects: id-eviction and the tug-of-war
counter); the branch hangs off the one existing call. On the true first boot the purge is a
no-op (nothing recorded yet), so behavior there is unchanged.

### Scope

- **Region pass**: the panel bug above; the purge runs on every Fresh region root.
- **Dialog dock tick** (`state == Fresh` branch, before its child sweep): the 8/7/6
  descendant-count rot shows dialog interiors suffer identically, so the dialog paths call
  the same purge on Fresh. Gated behind `DockDialogs=1`.
- **City pass**: the invariant (Fresh root implies new descendants) is structural, not
  region-specific, and the same call site covers it automatically. City HUD panels that
  persist across city loads classify AlreadyScaled and are never purged, so the documented
  double-scale hazard is untouched.

### Why not the alternatives

- **Clearing scaleMap on region re-activation**: too blunt - region records coexist with
  live city/dialog records in one map, and global clears are the canonical 2x->4x hazard.
- **Re-arming the stability gate on switch**: does nothing for this bug (the pass already
  runs AFTER the rebuild is complete - classification, not timing, fails) and rebuilds are
  tick-atomic.
- **Watching the region-name text for changes**: no proven-safe caption getter exists on
  this binary, text changes do not move geometry anyway, and the Fresh root is a strictly
  more reliable rebuild signal that requires no new vtable calls.
- **Relaxing Classify for id==0 records (evict on any size mismatch)**: this also fixes the
  panel but weakens the Unrecognized protection everywhere (a game-resized anonymous window
  would get re-scaled). It stays in reserve for the one edge case the purge cannot cover: a
  child created AFTER the purge pass at a recycled foreign address.

### Regression oracle

To re-verify the purge on any build:

1. Rebuild, boot to region: expect the unchanged boot signature
   (`region panel 0x09EBE9EE - 9 windows scaled`) and a clean region info bar.
2. Perform 3-4 live switches including a pop-0 to 1.26M pair (Kanto Tokai to Fairview):
   every switch pass logs **full boot-equal counts** for all nine panels (0x09EBE9EE = 9,
   0x6A91DC14 = 3, 0x09EBEE45 = 18, 0x09EBEE60 = 10) - the count table in section 1 is the
   regression oracle; any N below the boot value means a descendant was skipped again.
3. Verify the population number sits in the bar band after each switch: the label origin
   lands at absolute (88,1462).
4. With `DockDialogs=1`, reopen Load Region 5+ times: the descendant count stabilizes at the
   full value (8) instead of wandering 8/7/6.
5. Enter a city afterwards and confirm the city HUD scale-up still logs its usual counts (no
   double-scale guard lines) - guards remain as backstop.
