# SESSION RECORD — 2026-08-03 (afternoon → evening), v2.55.0 → v2.62.0

Written immediately before a context compaction. **If you are resuming, read §1
and §2 first**; everything after is the evidence behind them.

---

## 1. ✅ DONE — #110 CLOSED v2.63.0, USER-CONFIRMED (2026-08-03 22:0x)

> **"fix the broken Xs in the budget menu"** — fixed. The X was OURS, not stock.

**#103's NOT-A-BUG verdict was REFUTED**, and the way it happened is the lesson
of the day. Everything below §1 that cites #103's verdict is stale; the
`BUDGET-POPUP-X.md` brief now carries a refutation banner at the top.

**How it fell:** the user simply ran the game at 1x with the whole scaling layer
parked (`Set-StockCompare -Mode Stock`, 1024x768) and clicked the X. **It closed
the box.** Two minutes, no build. That single click overturned a day of correct
disassembly that was pointed at the wrong code path.

**The real cause, ours since v2.28.2.** Window `0x0423278D` is built by TWO
functions with different stock heights, and the POPBOX pin applied the ORDINANCE
twin's 125 to both:
* `sub_78B120` ordinance description popup — stock H 125, backdrop `0x384/0x484`,
  host = the Ordinances dialog (~754 tall at 2x). Correct.
* `sub_77BEC0` empty-ledger box — stock H **100**, backdrop `0x385/0x485`,
  close-X `0xCC/0x1CC`. **Its host IS the box**: a top-level 600x127 window, 127
  only because `CodePatches` hits the `push imm8` ceiling (`round(100*2)=200`
  will not encode).

Pinning that popup to `round(125*2)=250` inside a 127-tall host made the pin's
own y clamp resolve to `127 − 250 = −123`, so the popup — and the close-X at
popup-local y=22 — sat at host-local **y = −101, above the host rect**. The
sprite still drew (the engine does not clip it); the router's hit walk only
descends into children whose rect CONTAINS the point, so the click never arrived.
Logged **19 times** as `POPBOX 600x127 -> 600x250 at y=-123` and read past every
time.

**Isolated, not argued:** `PopupWrap=0` at 2x restored the X immediately *and*
reintroduced the ordinance twin's text clip — which is exactly why the cure is
per-twin and a kill switch is not a fix.

**The fix (v2.63.0):** twin gate on `0x484` vs `0x485`. Ordinance path is
BIT-IDENTICAL — the v2.28.4 math is kept, not re-derived. The ledger twin uses
its own stock height 100, and host + popup + content + `0x485` + `0x385` move
together to `round(100*f)` — a coupled set, all five or none, so the clamp is a
no-op BY CONSTRUCTION. New `POPSEEN` line gives the pin the reachability
instrument it never had.

Measured after (live log): `POPBOX 600x127 -> 600x200 at y=0`, body
`(30,50 510x100)` wrap 500 — was 27px. Ordinance unchanged at `780x250 y=504`.

**TWO NEW LAWS (47, 48) — in `feedback-sc4-scaling-laws.md`:**
1. A control that DRAWS right but does not RESPOND: check whether OUR geometry
   pushed it outside an **ancestor's** rect. Sprite and hit box share a rect —
   but only within an ancestor chain that still contains the point.
2. A gate can be RIGHT about its bytes and WRONG about the question. #103's gate
   decoded the command dispatch correctly and passed a real positive control; it
   was never shown that a *click* reaches that handler. It does not.

**Still genuinely unknown, deliberately untraced:** which route a click on `0xCC`
actually takes. Candidate is the notification target wired at `0x77C342`. Nobody
needs it now the geometry is right — but do not re-quote the dispatch analysis
as if it described the click path.

Stock aside, worth knowing: the WinProc closes this popup on **ESC / ENTER / F4**
(`0x78BCFE` — ChildRemove + Release + post). It was never a soft-lock.

### The user's next direction
> **"I want to fully complete 2x before we look into other scales"**

So 1.5x-only and 3x-only work is DEFERRED — that includes #109 (1.5x data-view
crash) and the new **#111** (package selection reads the ini factor, not the
computed tier, so tier 1.50 ships 2x dats + 2x fonts on 1.5x geometry).

---

## 2. STATE OF THE BUILD

**v2.62.0 deployed and hash-verified.** Config: 2400x1600 FullScreen, tier 2.0,
`ScaleAll=1`, all patch families ON, `SpinProbe=150`, `SpinFix` defaulted ON.

`_tests\Deploy-OnGameClose.ps1` now also **preserves the previous SC4UIScale.log
into `_tests\captures\` before deploying** — the log is recreated every launch and
that silently destroyed a spin capture earlier today.

---

## 3. #104 — THE SHUTDOWN HANG. Mechanism CONFIRMED, symptom fix WORKING (1 run)

### The disease (the GAME's, not ours — verified by reading our own source)

Service priorities decide the order, and they are unconditional:
```
cGZWinMgr        [+0x10] = 0x1312D0 = 1,250,000
cGZMessageServer [+0x10] = 0x4C4B40 = 5,000,000
RemoveAllSystemServices (0x0087AA81) erases leftmost-first => ascending
   => the WINDOW MANAGER always destructs FIRST
```
`~cGZWinMgr 0x009DC172` → `0x0099784E` = hashtable dtor → `clear() 0x0097C1A2`
frees every node, zeroes all 1543 buckets, **frees the bucket array**, and
**never rewrites `[set+4]`/`[set+8]`**. Those stale pointers are exactly what our
probe read as "1543 buckets, 0 entries".

Then three stacked stock defects:
1. `cGZWinGen::Init 0x0099AFA8` self-subscribes (`AddNotification` at
   `0x0099B051`) and that **AddRefs** the window. The only unsubscribe is in
   `Shutdown 0x0099A804`, gated on `GetFlag(0x4000)`.
2. `ChildRemove 0x0099E2BD` orphans a child **without calling Shutdown** — parent
   NULL, still subscribed, refcount 1 held by the notification map.
3. `cGZWin::ChildDeleteAll 0x0099DD6F` ORs the removal failure into `bl` at
   `0x0099DDA4` and **never tests it**; its only exit is an empty list.

`~cGZMessageServer 0x0092FE56` then drains its notification map at `srv+0x6C`,
releasing those orphans. Each one's `~cGZWin` runs `ChildDeleteAll`, every
`DoDestroyWindow 0x009DB0FD` sees `IsWindowValid == FALSE` (the set is gone),
returns FALSE having unlinked nothing, and the loop retries forever.

**Intermittency explained:** hang iff the session orphaned at least one window.
Tree-reachable windows are shut down by `cGZWinMgr::Shutdown`'s root walk
(`0x009DB2E9`) and unsubscribe cleanly. Falsifiable prediction: **a session that
never opens Budget should exit clean every time** — which matches bisect run 6.

### The fix (v2.62.0) — symptom only

`SpinProbe.cpp`, inside `SampleOnce`, at the instant the sampler already holds
the thread suspended with EIP inside `ChildDeleteAll`: point the list sentinel at
itself (two 4-byte writes) so `cmp edx,ecx` finally reports empty.

* **No game code is called.** The obvious repair (`parent->ChildDelete`) was
  specified as vtable `+0x3C`; the LIVE vtable has `0x0099EA6B` there, not the
  expected function — calling it would have run something unknown. And its helper
  reads the **freed** bucket array.
* Guards: only on a MEASURED spin; thread suspended; **refuses if the iteration
  guard `[list+4] != 0`**; every pointer range-checked; nothing logs inside the
  suspension; repeats per DISTINCT sentinel (max 64) and remembers what it fixed.
* `[UiSpike] SpinFix=0` disables it.

### Evidence
```
21:00:52.363  SHUTDOWN done
21:00:55.491  SPINFIX APPLIED #1 win=0x2C672A14 sentinel=0x338BCB94
21:00:55.491  <last line - sampler died with the process>
```
The sampler was armed for 120 s and writes a partial EVERY second. Zero further
lines ⇒ the process exited within ~1 s of the fix. Contrast the 20:54 run, where
the same fix applied and the thread kept accruing samples (218 → 261) with the
log running on for seconds.

**NOT YET ESTABLISHED: one clean run.** The recorder appends a row per launch;
`_tests\Show-104Rates.ps1` gives the rate. Do not close #104 on this.

---

## 4. WHAT ELSE CLOSED TODAY

| # | outcome |
|---|---|
| **#99** | coverage instrument fixed and now self-testing (4 injected defects rejected, incl. a silent 48-root drop the old guards passed as `[OK]`) |
| **#101** | RESOLVED — **not** a layout bug. The TIER GATE admits resolutions with no slack. User-confirmed clear at 1600x1200 |
| **#102** | `0xAA3AC002` is the **Taxes editor popup**, decided by 14 identical live captures + the script's own `caption="Taxes"`. Comments corrected in 4 files; behaviour unchanged |
| **#106** | combination gate built — 268 spans, 0 byte overlaps, flags 6 split-ownership regions incl. the #104 pair |
| **#100** | **DO NOT SHIP** the 4x bubble art — flipping the flag alone predicts 8x at the 2x tier (#98's exact shape) |

### Coverage is now 67.5%, canonical by user decision
`79/117 distinct root ids`. Not a regression — we stopped counting the flattering
way. The old 94.9% / 96.6% figures use different denominators and are **not
comparable**; `coverage_rederive.py` prints the canonical line and says so.

### #101's real defect, which is NOT 1.5x-specific
```
1400x1050 tier 1.5  dashboard 1320px = 94% of width,  80px spare -> OVERLAPPED
1600x1200 tier 1.5  dashboard 1320px = 82% of width, 280px spare -> CLEAR
1920x1440 tier 2.0  dashboard 1760px = 92% of width, 160px spare -> UNTESTED
```
`ScaleTier::Decide` gates on `880*f <= width`, admitting a resolution where the
dashboard exactly fills the screen. **The gate needs slack, for every tier.**

### 1080p cannot do 2x, for a real reason
`kTallestDesignPx = 558` is the **Graphics Options dialog**. At 2x it needs 1116px
of height; 1080p has 1080. The 36px that falls off is its Accept/Cancel row.
Unlocking it means making that one dialog an exception — a coupled change, and
worth measuring the next-tallest element first in case the blocker just moves.

---

## 5. STILL OPEN

| # | what |
|---|---|
| **#109** | **1.5x-ONLY CRASH** — opening a data view kills the game at tier 1.50, clean at 2.0. Logs preserved. Untested control: tier 1.5 with `ScaleAll=0` |
| **1.5x package bug** | ⚠ **FOUND, NOT FIXED.** At tier 1.50 ScaleTier activated the **2x** packages and disabled the **15x** ones, and copied `FontStyle-2x.ini`. Geometry 1.5x, art+fonts 2x. Explains "icons don't look sharp". `Settings: factor=2.00` while `AutoScale: tier 1.50` — package selection reads the INI factor, not the computed tier. **This may also be #109's cause.** (`-15x` is the tag for **1.5x**; the dot is dropped for filenames — confusing, worth renaming) |
| #97 | two-knob scaling |
| #98 | reopen only with a screenshot first |
| #102 residue | `0xAA921F4F` needs a 4th base size (330x109, region-screen Quit confirm) — REPORTED not fixed; needs on-screen check. Also: the collision gate keys on LINE ANCHORS, so comment edits re-report the same pairs as NEW |
| #108 | pre-GitHub privacy sweep: 584 text hits / ~190 files, 654 MB unreviewable binaries. Audit tool built. Decision made: **private repo, code-only** |
| #54/#75/#31/#70 | coverage residue, 1.5x rounding, stock-parity |

**Repo decision:** private, **code-only**. The dat pipeline was proven
reproducible — all three dats rebuilt content-identical, differing only in the
DBPF header timestamp (`DbpfPack.cs:123` stamps `UtcNow`, so byte-identical is
impossible by construction; mask offsets `0x18..0x1F`). One file
(`z_SC4UIScale_Art_2xHQ.dat`, 110 MB) exceeds GitHub's hard limit anyway, and
~226 MB is a dead blanket-2x branch that was explicitly abandoned as unsafe.

---

## 6. THE METHOD LESSON OF THIS SESSION

**Twelve hypotheses died on #104. Every one was killed by a measurement; not one
was talked to death.** Three were mine.

More usefully: **three separate instruments were found incapable of reporting the
negative they were being quoted for.**
1. `coverage_rederive.py` — wrong denominator, quoted as an independent check on
   itself.
2. The stack scan — `if (!InGameImage(v)) continue;` meant it could only print
   game frames, while the probe asked whether the top frame was in a different
   module.
3. `ReplicateIsWindowValid` — returned FALSE for every window ever passed to it
   and had **no positive control**; "the child is not in the valid set" was
   reported as THE MECHANISM on its word alone.

Two of those three were mine, and the third had been quoted for weeks. The cure
each time was the same: **make the instrument prove it can produce the opposite
result.** The self-test that finally cracked #104 did exactly that — it revealed
`entries=0`, i.e. the table was not healthy-but-empty, it was destroyed.

Also earned:
* **"buckets=1543" was inferred from the array being ALLOCATED, never POPULATED.**
  That wrong inference went into a workflow brief and steered three agents.
* **"The process vanished" cannot distinguish an exit from an End Task.** That
  ambiguity produced a false "it worked" report. The fix now measures whether
  game-code samples keep accruing.
* **A single-trial truth table on an intermittent bug is a row of coin flips.**
  The original 13-run bisect produced a "culprit pair" that dissolved on repeat.
* **Verify a vtable slot before calling through it.** `+0x3C` was specified;
  the live vtable had something else there.
