---
name: feedback-never-repin-a-fingerprint-without-reading-the-bytes
description: "When an exe-pinned offline gate says 'fingerprint mismatch', NEVER just re-pin it. Bypass the check, run every byte-level site assertion against the new binary, and re-pin only if they all pass — then write down that you did. Relaxing a guard because a tool said no is exactly how the CAM splash shipped."
metadata:
  node_type: memory
  type: feedback
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-06T04:15:28.174Z
---

# A fingerprint is a PROXY. When it fails, check the thing it stands for.

2026-08-05: three SC4UIScale gates printed `FAIL: fingerprint mismatch`
together and stopped adjudicating anything below that line. Two causes, and
separating them was the whole job:

1. **The 4GB/LAA patch flips one bit in the PE COFF Characteristics word.**
   It cannot change an instruction, but `exe_fingerprint()` hashed the whole
   file, so the hash moved. Cured by MASKING `0x0020` before hashing — every
   existing pin was taken with the bit clear, so masking keeps them all valid
   in both directions (patch and `-Undo`).
2. **The reinstall produced a genuinely different binary of the same size.**
   The build the gates were derived from no longer exists on disk to diff.

For (2) the only honest move is: **bypass the fingerprint, run the gate's own
byte assertions against the new exe, and re-pin only if every one passes.**
All three did (24/24 site checks in one of them), so the re-pin was earned.

**Why this matters more than it sounds:** relaxing a guard because a tool
returned a negative is precisely how the #140 startup splash shipped CAM's
artwork instead of the game's. Same reasoning, same session, one file apart.
A fingerprint stands in for "the code is what I think it is" — reading the
bytes at the actual VAs *is* that claim, directly, and is strictly stronger.

**How to apply**
* On a mismatch: bypass → assert → re-pin → **comment the re-pin** with what
  was verified and why the old binary is gone. An unexplained pin change is
  indistinguishable from someone silencing a gate.
* Expect the whole exe-pinned family to go red *together* after any reinstall
  or exe patch. Together is the instrument working. One gate red while its
  siblings are green on the same binary means the gates disagree about what
  "the same build" means — and the cause is usually a **private copy of the
  fingerprint function** (there were three; there is now one).
* Never let a gate ship a verdict it did not measure. These correctly refused.

Related: [[feedback-null-is-not-evidence]],
[[reference-sc4-intro-dat-is-the-eighth-archive]],
[[feedback-static-defect-is-a-hypothesis]], [[feedback-sc4-regression-net]].
