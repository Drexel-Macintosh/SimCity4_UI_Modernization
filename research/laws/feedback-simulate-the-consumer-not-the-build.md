# Model the Consumer, Measure the Shipped File

A build reporting its own success is not evidence. A generator graded by its own
restatement of its own intent will pass while the screen disagrees, and it will
keep passing for as long as the grader and the generator share a definition of
"correct".

The failure mode is concrete: a run of consecutive "fixed" claims can all be
true statements about what the build did — "realigned", "residual `[0,0,0,0]`",
"packed 528x132", "registered=2" — and none of them a statement about what the
game would draw. Every one of those metrics is produced by the same code whose
output is in question.

What breaks the deadlock is a simulator that reproduces the engine's own crop
and runs it against the deployed file rather than the build directory or any
intermediate. For a state strip the engine's source rectangle is

    source origin = state index * stride
    source extent = one stride

so the consumer's view of frame N is fully determined by the stride, and any
generator whose stride disagrees with the packed sheet is off by whole or
fractional frames no matter what its own residual reports. Two "aligned"
metrics can exist and disagree on the same file: the generator's residual reads
`[0,0,0,0]` while the consumer model reads `[0,0,-1,-1]`. The consumer model is
the one that matches the screen.

Practice:

- Before claiming a fix, model the consumer and run that model against the
  shipped artefact, not the build tree and not an intermediate.
- Make the solver optimise the same function the gate asserts. One definition of
  correct, end to end; two definitions guarantee that one of them is decorative.
- A green instrument that does not move the screen means the instrument is on
  the wrong channel. The next action is to prove the probe *can* see the
  subject, never to believe the null.
- Keep the known-broken input as a positive control that must still fail. A gate
  in which nothing can fail is not a gate, and a gate loses that property
  silently the first time the harness stops feeding it the broken case.
