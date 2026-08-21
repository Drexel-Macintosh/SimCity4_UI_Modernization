# Prize Versus Blast Radius

## State the prize and the blast radius before writing code

Quantify both sides of the trade before rebuilding any mechanism that currently
works. A representative upside-down trade: the prize was a 1-2 frame flash
(20-36 ms) during flyout open; the proposed change was rebuilding how working
menus are constructed. No amount of engineering quality makes that trade
correct, because the downside is a menu that no longer opens and the upside is
half a frame of colour.

Ask, in order:

1. What exactly does the player get, expressed as a number (pixels, milliseconds,
   frames)?
2. What breaks if the change is wrong — a cosmetic residual, or a control that
   stops working?
3. Does a smaller mechanism already exist? Tightening a proven path beats
   building a new one.
4. Can the offline model answer the question before any code ships?

## A constant is never alone

Immediates in `.text` are rarely independent inputs; they are terms in
relationships that other subsystems read. Moving one `push imm8` drove a value
200 bytes away, in a different subsystem, negative:

```
[+0xEC] = artHeight − 2 × [+0xE8]
```

Measured outcomes for that field: stock 3; constants changed alone **−47**
(renders as a sliver); art changed alone 56; both changed together 6.

Before changing any constant, ask the model two questions: what reads it, and
what is computed from it. If a fix has two halves that are computed from each
other, they ship together or not at all. If shipping both halves still produces
a wrong value, a third term exists in the relationship — stop and find it
offline rather than tuning by build.

## The game is simulated — model first, game last

`tools\uimap\` is a working offline model of the UI layout, and every
"what if this changes?" has an answer there that costs minutes and cannot break
anything:

- A builder census and a constant map — which builder owns a window, which
  constants that builder uses, their encodings and their twins.
- `emu\emu_layout.py` — runs the game's own layout code under Unicorn and
  predicts rects at any scale factor.
- `diff\` — predicted versus live versus stock at f = 1, 1.5, 2, 3.

A shipped experiment, by contrast, costs a build, a deploy, a play session, and
sometimes a working UI.

## "It worked for panel X" is not evidence about panel Y

Choose a cure from the window's construction type — see
`tools\research\SC4-UI-ENGINE.md` §4.7, which classifies windows by how they are
born — never by analogy to a panel that looked similar. Data pre-scale cured the
advisor strip and broke the composed city HUD.

Canonical procedure: `tools\research\METHOD.md` §6A.
