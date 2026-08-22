# NN vs HQ 2x Upscale Comparison — SimCity_1 UI Art

Date: 2026-07-21. Source: `tools\dbpf\extracted\SimCity_1` (2,206 PNGs).
NN batch: `tools\upscale\preview\SimCity_1` (packed as `z_SC4UIScale_Art_2x.dat`, 32.8 MB).
HQ batch: `tools\upscale\preview-hq\SimCity_1` (packed as `z_SC4UIScale_Art_2xHQ.dat`, 109.8 MB, 2,206 entries).

Each pair below is a straight copy of the corresponding batch output (`<instance>-nn.png` / `<instance>-hq.png`), same TGI, same output dimensions.

| Instance | Class | Output dims (source) | NN bytes | HQ bytes | Assessment |
|---|---|---|---|---|---|
| 0x0c0729aa | Toolbar/frame strip (compass-rose rotation frames) | 6960x112 (3480x56) | 411,250 | 1,498,712 | NN keeps the star points and fine spokes crisp; HQ softens every point and bleeds the yellow needle. Partial-alpha pixels rise 4.27% -> 8.36% (new soft edge ring = halo risk on the round icons). NN wins. |
| 0x13d14ca0 | Mid-size dialog gadget art, magenta colorkey background | 470x444 (235x222) | 45,070 | 143,359 | Decisive. The art sits on pure FF00FF colorkey. NN: 101,640 pure-magenta px, only 4 near-magenta blends. HQ: 1,467 near-magenta blend pixels smeared along the gadget silhouette — if the engine keys on exact FF00FF these render as a pink fringe in-game. NN wins outright. |
| 0x140155e9 | Small icon, building glyph | 48x48 (24x24) | 1,423 | 4,016 | At icon size the HQ output is visibly blurry — spire and bar edges smear into each other. NN stays blocky but crisp, which is how the original pixel-art icon was designed to read. NN wins. |
| 0x14416300 | Alpha-edge gadget (rounded shapes, soft baked shadow) | 816x204 (408x102) | 9,635 | 33,878 | The source already carries hand-baked anti-aliased edges; NN preserves them exactly (and keeps the magenta RGB parked under alpha=0: 73,536 px). HQ recomputes RGB in/near transparent regions (pure magenta drops to 0) and softens the silhouette — classic alpha-halo precondition when the engine filters at draw time. NN wins. |
| 0x144161f8 | Text-bearing dialog art (newspaper with newsprint copy) | 880x456 (440x228) | 48,068 | 158,930 | The one class where HQ is defensible: the faux-newsprint looks more "print-like" smoothed. But the text is decorative texture, NN keeps it perfectly readable, and the frame border stays sharper under NN. Marginal HQ aesthetic gain, not worth the mode split. Tie, slight NN. |
| 0xcbcba950 | Random pick — gauge/dial frame strip | 5610x100 (2805x50) | 80,882 | 203,888 | NN keeps 1px tick marks, needles, and the dithered cyan arc texture intact. HQ merges adjacent ticks, blurs the needle, and melts the dither into flat gradient — detail loss on exactly the elements a gauge needs. NN wins. |

## Verdict

**Ship NN (`z_SC4UIScale_Art_2x.dat`) as the default.** Three independent reasons:

1. **Colorkey fringing.** A significant share of this art uses FF00FF colorkey rather than alpha. HQ's resampling blends the key color into silhouette edges (1,467 fringe pixels on 0x13d14ca0 alone) — a visible pink halo risk in-game. NN can never produce a non-key color.
2. **Design intent.** Maxis authored this art at the pixel grid with baked anti-aliasing. 2x NN reproduces exactly that art, just bigger; HQ second-guesses it and blurs 1px ticks, icon edges, and glyphs — worst on the smallest, most UI-critical assets.
3. **Cost.** HQ triples the package: 109.8 MB vs 32.8 MB (smoothing destroys PNG's palette/run compressibility) for no per-class win.

Keep `z_SC4UIScale_Art_2xHQ.dat` on disk as an A/B candidate only; if any single asset ever looks better smoothed (photographic textures like the newsprint), cherry-pick that instance rather than switching the default.
