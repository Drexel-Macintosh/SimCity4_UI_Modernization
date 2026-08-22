# MODE-C SESSION SHEET

**One sitting. ~12 minutes of game time. NO resolution change, NO stock flip.**

---

## What we are testing, and why you should expect "not a bug"

A static census flagged a handful of windows as possibly shipping **2x art inside a 1x box**
(or the reverse). **None of these has ever been seen misbehaving on screen.** They are
census-derived *suspicions*, not observed defects. The last time we shipped a cure for one
of these without an on-screen disagreement (#98) the "defect" did not exist and the fix
broke the UI. So this session exists to *look*, not to fix, and for at least one of the two
surviving items the expected outcome is **"correct, close it"**. A step that could not
change what we do next has been cut from this sheet; three of the original six items are
already closed offline and are listed at the bottom, not here.

---

## Before you launch (orchestrator does this, ~10 seconds)

Edit `<PROJECT-ROOT> 4\Plugins\SC4UIScale.ini`:

```
[UiSpike]
LiveDumpMs=1000        ; was 0
```

Leave everything else alone. `LogLevel=3` is already set. **Set `LiveDumpMs` back to `0`
the moment the session ends** — at 1000 ms this writes a full window-tree dump every second
(~850 windows, ~12 MB per session).

This is the **primary instrument**: `LiveViewDump()` walks the **whole tree from the main
window** (`src\UiSpike.cpp:5995-6001`), not from the 3D view, so it reaches windows our
scaling sweep can never touch. It prints, for every window:
`UI id=0x........ pos(x,y) size(WxH) children=N vis=? en=?`

The screenshot is the **second, independent** instrument (pixels vs. tree-walk = genuinely
different failure modes). Do not treat the two as one witness; read both.

**Capture command the orchestrator runs on each "go":**

```
"<PROJECT-ROOT> 1 Project\1 Completed Projects\SC4TouchControls\tools\capture\CaptureWindow.exe" "<PROJECT-ROOT> 1 Project\1 Completed Projects\SC4TouchControls\tools\research\_incoming\modec-captures\<STEP>.png"
```

It uses `SetProcessDPIAware` + `PrintWindow(PW_RENDERFULLCONTENT)`. **It does not steal
focus and it does not click anything.** Every capture must come out exactly **2400x1600**;
if it does not, discard it rather than measure it.

---

# THE SHEET

Configuration for **every** step below: **OURS — 2400x1600, scaling layer enabled, normal
play settings.** No stock capture is required by any step. **Zero config flips.**

## Step 1 — Launch, load a DEVELOPED city of your own

Not a Timbuktu tutorial tile and not an empty "New City" — a My Sim has to move into an
existing occupied house. Any of your built cities.

*Say "in" when the city has finished loading.* No capture here.

## Step 2 — Arm the "Change My Sim's House" tool  → **SURFACE A3**

1. Bottom-right dashboard puck → **My Sim Mode**.
2. If no Sim exists: **Move In My Sim** → wizard → **Accept**.
3. Select the Sim → **Expand**.
4. Click **Change My Sim's House**. The Sim's portrait now rides the cursor.
5. Move the mouse over open terrain and **hold it still** — say "armed".

Orchestrator captures `A3-armed.png` and reads the next `LIVE full-tree dump` block.

**POSITIVE CONTROL (check this BEFORE reading any verdict).** The orchestrator must have
one dump from Step 1 (tool not armed) and one from Step 5 (tool armed). Window
`0x27DF05BE` / `0x27DF05BF` is **created by the tool** — it must be **ABSENT** in the first
and **PRESENT** in the second. If it is absent from both, the instrument did not see the
surface; that is a null, **not** a pass. Retake, do not record.

**PRE-COMMITTED VERDICTS.** At 1x the tree reads: root `0x27DF05BE` size **46x97**,
`children=2` — portrait `0xEA9457BA` at **pos(5,5) size(36x41)**, plus one unnamed frame
child at **pos(0,0) size(46x97)**.

| dump reads | verdict | what we do |
|---|---|---|
| root **46x97**, portrait **36x41** | **NOT A BUG (Mode A).** Chip is uniformly 1x — coherent, just small. No Mode C anywhere. | Close A3. Log a separate low-priority "unswept but coherent" note. Ship nothing. |
| root **92x194**, portrait **36x41** at (5,5) | **Mode C CONFIRMED** — a real defect, and it *refutes* our "main-window ⇒ unswept" claim. | Open a task. **Do NOT use `kBmpxDialogRoots`** — `0x27DF05BE` collides with the Obliterate City confirm and that list is id-keyed. |
| root **92x194**, portrait **72x82** at (10,10) | **Already correct — and this refutes our own data model**, since `refmap*.csv` stages no 2x art for it. | Report as a finding: something we have not read is supplying the art. |
| id present but children truncated / depth-capped | **INCONCLUSIVE** (`kMaxDepth=8`). | Fall back to the screenshot ratio below. |

**Screenshot cross-check (independent):** portrait width ÷ chip outer width.
**0.78 ± 0.03 = 1x chip. 0.39 ± 0.03 = Mode C.** These differ by 2x; no capture error
crosses them. If the ratio and the dump disagree, trust the ratio and re-take.

## Step 3 — Swap the chip state (5 seconds, confirms the instrument, not the defect)

Move the cursor **over an existing house** (a legal target), hold still, say "over house".
Orchestrator captures `A3-legal.png`.

**What it decides:** whether we were looking at the live chip at all. `0x27DF05BE` and
`0x27DF05BF` carry different frame BMPs (`13f15213` / `13f15214`). If the frame art changes
between `A3-armed.png` and `A3-legal.png`, the object under measurement is confirmed live
and correctly identified. If nothing changes, Step 2's verdict is downgraded to
**PLAUSIBLE** and needs a retake. **Right-click / Esc to cancel — do not move the Sim.**

## Step 4 — (OPTIONAL, ~30 s, you are already here) Open the Budget panel

Only if Steps 2-3 went smoothly. Open **Budget**, leave it open, say "budget".
Orchestrator reads the next dump.

**What it decides:** id `0xAA3AC002` is in **two** of our lists whose **own comments name
two different windows** ("Taxes editor popup" vs "budget income section") — the exact
"our comment is lying" pattern that produced #98.
- **PASS:** `0xAA3AC002` appears **exactly once**, at **1000x404** or **1000x928**.
- **FAIL:** it appears **twice**, or once at 500x202 / 500x464 (unscaled), or at a size
  matching neither script.
Close **Esc**.

## Step 5 — Exit to region, then Main Menu → Load Region → **Timbuktu** → enter **"Getting Started Tutorial"**

If no tutorial page opens, they were already consumed: from the region screen use
**Play Options → Reset Tutorials**, then re-enter. **If a tutorial still will not start
after one retry, STOP — say so and end the session.** B yields nothing without it, and the
sheet is over.

Once the tutorial page is on screen, **wait 3 seconds and do not click Continue yet**.
Say "tutorial". Orchestrator captures `B-page.png` and reads the next dump.

**POSITIVE CONTROL:** the tutorial page `0x4A35B0F2` must be present in the dump **and**
visible in the capture. Both overlays are built in the *same function* as the page
(`sub_443E60`), so if the page is there and `0x0A41C7B2` / `0x0A41C7B3` are not, the
instrument was too shallow — that is a null, not an absence.

**TWO verdicts from this one capture:**

| observation | PASS | FAIL |
|---|---|---|
| tutorial page `0x4A35B0F2` | **946x616** — the static double works (never before confirmed eyes-on) | **473x308** — the dialog-static package is not reaching tutorial pages |
| overlays `0x0A41C7B2`/`B3` | **124x98** — scaled, close B | **62x49** — 1x, open a task |

The overlays are born `vis=0`. **Their SIZE in the dump settles B regardless of
visibility** — you do not need to make one appear.

## Step 6 — Done

Say "done". Quit the game normally. Orchestrator sets `LiveDumpMs=0` and archives
`SC4UIScale.log`.

---

# NOT IN THE SHEET — closed offline, do not spend game time on these

- **Grid popup `0xEACA96DD`** — the shipping exe never loads its script (0 occurrences of
  `0x6ACA9687` / `0xEACA96DD`, with the same scan finding `0x6A9455C9`, `0x0A41BE3E/3F`,
  `0x27DF05BE`); no other `.UI` of 330 references it. Unreachable, and its `blttype=edge`
  art degrades invisibly even if it were. **Closed.**
- **46x108 chips `0x6BFAC122`+`0x8BFAC13E` and `0xCBFACAE1`+`0x8BFAC13E`** — superseded
  generation of the Step-2 chip. Their ids and script instances occur **0 times** in the
  exe under a scan whose positive control passes. A screenshot could only ever *confirm*
  them, never refute them. **Closed as unreachable.**
- **`0x4A35B0F2` vs `0x0A2DD355` discrepancy** — not a contradiction: `0x0A2DD355` is the
  script instance, `0x4A35B0F2` is the window id inside it. **Closed.**
