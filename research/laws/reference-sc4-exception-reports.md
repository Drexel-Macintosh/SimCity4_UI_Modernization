# SimCity 4 Exception Reports

SimCity 4 installs its own top-level exception handler and writes a crash report
to disk before exiting. On any crash, that file is the first thing to read — it
is a free measurement of where the game died, already on disk, requiring no
rebuild, no debugger and no reproduction attempt.

## Location and contents

```
%USERPROFILE%\Documents\SimCity 4\Exception Reports\
    SimCity Exception Report YYYY.MM.DD HH.MM.SS.txt
```

(If Documents is redirected to a cloud-synced folder, the reports follow it.)

Each report carries:

* the exception code (e.g. `ACCESS_VIOLATION`),
* `CS:EIP` — **the faulting instruction address**,
* the full register set at fault time,
* `Section:Offset` for the faulting address,
* the executable version (`1.1.641.0` for the current Steam/patched build),
* the loaded-module list with base addresses, which identifies injected DLLs and
  their load bases so an EIP inside a mod can be resolved to a module offset.

Because the exe has a fixed `ImageBase` of `0x400000` and is not relocated in
practice, an EIP inside the game's own range maps directly to a static address in
a disassembly of `SimCity 4.exe` — no rebasing arithmetic required.

## Windows Error Reporting is a structural null here

The game's handler catches the fault, writes its report, and exits cleanly from
the operating system's point of view. As a result there is typically **no
`Application Error` event in the Windows event log and no `.wer` or `.dmp`
produced** for a SimCity 4 crash. "WER recorded nothing" is therefore not
evidence that no crash occurred, and not evidence about where it occurred; the
channel simply never sees the fault. Check the game's own Exception Reports
directory instead.

## Correlating with a mod log

Match report timestamps against the tail of the mod log. A logger that flushes
per line survives the crash, so the last lines written before the fault are
intact and can be lined up with the report's clock time. That pairing turns a
bare EIP into a sequence: which panel was being scaled, at which tier, at the
moment of the fault.

## Worked case: five reports, one instruction

Twelve reports accumulate across a series of runs. Five of them fault at the
**identical instruction `0x00910010`** — an `ACCESS_VIOLATION` inside the game's
`rep stosd` row fill — at UI scale tier 1.5x and tier 3x alike, and **never at
2x**.

That distribution is itself the diagnosis. One instruction, crashing at two tiers
and clean at a third, cannot be a random memory error or a general size problem;
it is a geometry invariant that holds at 2x and breaks at the other two, and the
tiers that break versus the one that does not name the invariant.

Measured against the crashing runs, the surface size `blitSize` is exact at both
crashing tiers (1.5x: 256 = 64 << 2; 3x: 512 = 64 << 3), so the surface itself is
never the overrun. The 384 and 768 figures belong to the **window** size, one
level out from the surface.

The invariant is that the **window** and the **surface** disagree.

| tier | window / surface | result |
|---|---|---|
| 1.5x | 384 / 256 | crash |
| 2x   | 512 / 512 | fine |
| 3x   | 768 / 512 | crash |

The window is `ScaleRound(256, f)`; the surface is created at `blitSize`. They
agree only when the scale factor is itself a power of two. The fix snaps the
window to the largest exact power-of-two multiple of the terrain dimension within
the bake ceiling, which is why that window can only ever be 256, 512 or 1024 —
never 384 or 768.

## The rule

On any crash, list the Exception Reports directory before reasoning about bytes.
A faulting EIP is a measurement; an inferred cause is a hypothesis. If two reports
at different configurations share an EIP, the discriminator is in hand before a
line of analysis has been written — and if a third configuration with the same
code path does *not* crash, that contrast usually names the invariant outright.
