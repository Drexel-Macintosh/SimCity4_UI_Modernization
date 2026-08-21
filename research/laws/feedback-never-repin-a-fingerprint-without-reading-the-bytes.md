# Exe Fingerprint Gates and the 4GB Patch

Several offline gates pin themselves to a hash of the game executable so that
byte-level assertions about specific virtual addresses are only adjudicated
against the build they were derived from. A fingerprint is a proxy for the
claim "the code at these addresses is what the gate thinks it is". When the
proxy fails, the thing it stands for still has to be checked directly.

## The 4GB / large-address-aware patch moves the hash without moving any code

The LAA patch sets the `IMAGE_FILE_LARGE_ADDRESS_AWARE` bit (`0x0020`) in the
PE COFF header's `Characteristics` word. That single bit cannot change an
instruction, but a fingerprint computed over the whole file moves anyway, so
every exe-pinned gate reports a mismatch on a binary that is functionally
identical at every address it cares about.

Cure: mask `0x0020` out of the `Characteristics` word before hashing. Pins
taken with the bit clear stay valid in both directions — patched and unpatched
— so the same pin adjudicates a binary before the patch, after it, and after
the patch is undone.

## A genuine mismatch: bypass, assert, then re-pin

A reinstall can produce a genuinely different binary, sometimes at the same
file size, with the build the gates were derived from no longer on disk to
diff against. The only honest move is:

1. Bypass the fingerprint check.
2. Run every one of that gate's byte-level site assertions against the new exe.
3. Re-pin only if all of them pass.
4. Comment the re-pin with what was verified and why the old binary is gone.

An unexplained pin change is indistinguishable from someone silencing a gate.
Reading the bytes at the actual VAs *is* the claim the fingerprint stands in
for, so a full site sweep is strictly stronger evidence than a matching hash —
but only if it is actually run.

Relaxing a guard because a tool returned a negative is precisely how a
third-party mod's artwork once shipped in place of the game's own startup
splash. The gate refused; the refusal was correct; overriding it without
measuring anything was the defect.

## Reading the failure pattern

* Expect the entire exe-pinned family to go red *together* after any reinstall
  or exe patch. Simultaneous failure is the instrument working correctly.
* One gate red while its siblings are green on the same binary means the gates
  disagree about what "the same build" means. The usual cause is a private
  copy of the fingerprint function that has drifted from the others; keep
  exactly one implementation and have every gate call it.
* Never let a gate ship a verdict it did not measure. A gate that refuses to
  adjudicate below a mismatch line is behaving correctly, and its silence must
  not be read as a pass.
