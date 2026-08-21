# A Static-Data Defect Is a Hypothesis

A defect found only in static data is a hypothesis until something on screen
disagrees with it. Do not fix it yet. Get an eyes-on symptom first, or prove the
runtime is not already handling it.

## The failure mode

A static census of the shipped `.UI` data can report, correctly, that a window
root holds "2x art in a 1x box" — and the fix for that report can still break
the screen. The Trip Types legend root is the worked example: the census read
the data accurately, printed a positive control for four absences
(`SCALED_WINDOW_IDS`, `kNeverScaleIds`, `kDataScaledSubtreeIds`, and the
dialog-static generator inputs), and its null therefore looked measured. The
data-side fix shipped and the legend rendered at 4x.

The runtime had already been scaling those windows through a fifth list the
census never consulted, `kRegionPanelIds`. One line of the live log settles it:

```
panel 0x0BB0F5E7 (152x203) -> (304x406)
```

The window was never wrong on screen. The data fix simply multiplied a scale
the runtime had already applied.

## Why a data-only gate cannot catch this

An offline adjudicator that checks the data against itself — `area` equals
`imagerect`, pitch at least art height — passes at every tier both before and
after such a change. A gate that measures data against itself proves internal
consistency, never necessity. It can say "these numbers agree"; it can never say
"this window needed changing".

## Rules that follow

1. A null is measured only when the positive control covers every path. Four of
   five lists is a structural null wearing a measurement's clothes — it reports
   absence from the places that were searched, which is not absence.
2. Before any data-side scaling fix, grep the live log for the window id. If the
   runtime already moved it, a data fix doubles it.
3. "Absent from every id list" proves nothing either. The runtime sweep is
   structural — it walks the window tree — so windows are scaled with no id
   recorded anywhere.

## The shape of the good path

The contrasting case is a 1.5x dashboard defect: it started from a screenshot,
was traced to a measured shear of -256 px, was checked against a stock control,
and its fix was replay-verified as a no-op at the already-working tier before
shipping. Identical rigour, opposite outcome, because the evidence started on
screen and the offline work only explained it.

Related laws: a probe that finds nothing is not evidence until the positive
control proves it could have seen the thing; two blind instruments agreeing
count as one; a gate is only as honest as its scope.
