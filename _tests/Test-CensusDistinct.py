"""Test-CensusDistinct.py - the census budget must bound DISTINCT names.

WHY THIS EXISTS
===============
The overlay census instrument failed twice on live play sessions, and neither
failure was visible as a failure - both looked like "the game does not spawn
those effects".

  Round 1  (2026-08-30): EffectCensus raised to 400, but the census branch is
           gated on MissionBubbleFx >= 3 and the ini left it at 2. The branch
           never ran. Cured by a startup warning when the budget is raised on
           a dead branch.
  Round 1b (2026-08-30): branch ran correctly, and 381 of 401 logged lines
           were industrial smoke. The budget was exhausted 88 SECONDS BEFORE
           the player picked up a tool, so the names being hunted could not
           have been recorded however the session was played.

Round 1b is the interesting one: the instrument was armed correctly and still
could not see. A bigger number does not fix it - ambient smoke is continuous
and eats any budget - so the census now spends its budget on DISTINCT names.

This test replays the REAL name sequence from the round-1b capture through the
same first-sight rule the DLL uses, and asserts the budget would no longer be
exhausted. It is a regression test for an instrument, which is worth having
precisely because a broken instrument reports success.
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURE = os.path.join(HERE, "captures", "2026-08-30-census-round1b.log")
SOURCE = os.path.join(HERE, "..", "src", "CodePatches.cpp")

failures = []


def check(ok, msg):
    print(("  PASS  " if ok else "  FAIL  ") + msg)
    if not ok:
        failures.append(msg)


def first_sight_sim(names, budget, seen_max=192):
    """Mirror of CensusFirstSight + the budget test in CodePatches.cpp."""
    seen, logged = [], 0
    for n in names:
        if logged >= budget:
            break
        low = n.lower()
        if low in seen:
            continue
        if len(seen) < seen_max:
            seen.append(low)
        logged += 1
    return logged, seen


print("Test-CensusDistinct - the census must bound distinct names\n")

# ---- the real sequence, in order, from the live capture --------------------
if not os.path.isfile(CAPTURE):
    print("SKIP - capture not present: %s" % CAPTURE)
    raise SystemExit(0)

raw = io.open(CAPTURE, encoding="utf-8", errors="replace").read()
seq = re.findall(r"BUBBLEALL ([A-Za-z_0-9]+)", raw)
distinct = sorted(set(s.lower() for s in seq))

print("Round 1b as it actually happened:")
print("    %d logged spawns, %d distinct names" % (len(seq), len(distinct)))
check(len(seq) >= 400,
      "the old rule exhausted its 400 budget (logged %d)" % len(seq))
check(len(distinct) < 20,
      "yet only %d distinct names were involved" % len(distinct))

# ---- what the new rule would have done on the SAME input ------------------
logged, seen = first_sight_sim(seq, budget=400)
print("\nSame sequence under the first-sight rule:")
print("    %d lines, %d names recorded" % (logged, len(seen)))
check(logged == len(distinct),
      "one line per distinct name (%d), not per spawn" % len(distinct))
check(logged < 400,
      "budget NOT exhausted - %d of 400 still available for new names"
      % (400 - logged))

# The load that broke it must no longer be able to break it.
smoke = [n for n in seq if "smoke" in n.lower()]
check(len(smoke) > 300,
      "ambient smoke dominated the raw sequence (%d spawns)" % len(smoke))
smoke_lines = first_sight_sim(smoke, budget=400)[0]
check(smoke_lines <= 10,
      "the same smoke now costs %d lines instead of %d" %
      (smoke_lines, len(smoke)))

# ---- a name appearing only AFTER the old budget died is now reachable -----
tail = ["PlopMode_Police_Inactive", "local_grid", "Lot_Direction_Arrow",
        "mountain_tool_active"]
logged2, _ = first_sight_sim(seq + tail, budget=400)
check(logged2 == len(distinct) + len(tail),
      "late tool-cursor names are still logged after a full ambient load")

# ---- the DLL must actually implement this ---------------------------------
src = io.open(SOURCE, encoding="utf-8", errors="replace").read()
check("CensusFirstSight" in src, "CodePatches.cpp defines CensusFirstSight")
check(re.search(r"gBubbleAllLogs < gEffectCensus\s*\n\s*&& CensusFirstSight",
                src) is not None,
      "the census branch gates on first-sight as well as the budget")
check("_stricmp" in src, "name comparison is case-insensitive")
check(re.search(r"MissionBubbleFx.{0,400}?CENSUS BRANCH IS GATED", src,
                re.S) is not None,
      "a raised budget on a dead branch still warns (round 1's cure)")

print("")
if failures:
    print("FAIL - %d check(s) failed" % len(failures))
    raise SystemExit(1)
print("ALL PASS - the census bounds distinct names, and the load that "
      "exhausted it twice no longer can.")
