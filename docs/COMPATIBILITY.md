# Compatibility

## Mods with a compatibility layer

| Mod | What the layer enlarges | Gated? |
|---|---|---|
| **Network Addon Mod** | 392 menu ItemIcons, drawn from NAM's own artwork | yes |
| **Colossus Addon Mod** | UI scripts and art | yes |
| **Allow More Building Styles** (null-45) | the Building Style Control dialog. The `.UI` script is **CoriBoom**'s, packaged inside null-45's mod | yes |
| **Save Warning** (cyclone-boom) | the in-city quit/exit confirmations | yes |
| **God Terraforming in Mayor Mode** (warrior) | the compact Landscape and Signs flyouts | yes |
| **Submenus DLL** (memo33) | 55 of its menu icons, drawn from that mod's own artwork | **no** |
| **Colossus Addon Mod** — chart caption | a caption record that CAM's Power and Water graphs request but that no installed file provides, leaving that legend row blank. The layer supplies the missing resource; CAM's own files are untouched | **no** |

**"Gated"** means the package is checked at load against the owning mod's file
and deactivates itself if that mod is not installed. The five gated rows are
the complete gate table in `src/ScaleTier.cpp`. The two ungated rows ship in
`ItemIconsSub` and `CamGraphLabels`, which load regardless — their entries are
keyed to resource ids only those plugins introduce, so without the plugin
nothing looks them up and they sit inert. Inert is not the same as gated.

**No scaling defect exists in any of those mods.** In every scaling case the
symptom belongs to this layer: it enlarges a container and the mod's
correctly-authored 1× artwork ends up inside it, tiled or half-size. With this
mod disabled they render exactly as their authors intended.

The one exception is the CAM chart caption above, along with the related
menu-data gaps reported to the CAM and SIM developers. Those reproduce with
none of this mod's packages installed and are genuine upstream data gaps —
worked around by adding a resource, never by editing CAM's files.

Where a mod is patched, the enlarged art is **that mod's own art**, never a
Maxis substitute — so what appears on screen is still that author's work, just
bigger.

### If you are one of those authors

Open an issue and the package comes out of the release. It's your artwork;
there's no argument to have. Removal degrades gracefully — that mod's UI simply
renders at 1× again and nothing else changes.

### If a NAM or CAM update changes an icon

The bundled copy becomes a stale picture until it is regenerated. Sizes are
deliberately **not** checked, because a size check would fail the whole package
on a harmless upstream change. Report it and it gets rebuilt.

## Known-good alongside

Any DLL plugin that doesn't lay out windows — SC4Fix, the memo33 family
(including the Submenus DLL, whose icons get the layer above), null-45's
gameplay DLLs, resource-loading hooks. This mod hooks window geometry and
layout constants only.

## Requirements and conflicts

- **SimCity 4 Deluxe 1.1.641.** The plugin verifies the version and disables
  itself on anything else.
- **Above 2048 px wide you need [dgVoodoo](http://dege.freeweb.hu/dgVoodoo2/).**
  DirectX 7 caps surfaces at 2048×2048; the game crashes without it at
  2560-wide and above. Not caused by this mod, but you will meet it here.
- **Another UI-scaling mod** will conflict. Only one thing can own the layout.
- **Windows DPI virtualisation** produces a superficially similar "everything
  is zoomed" effect that this mod does *not* cause and cannot fix. If the game
  looks stretched from the very first frame, check for a compatibility shim on
  the executable before blaming a plugin.

## Reporting a problem

Include:

1. Your **resolution** and which tier the log says it picked.
2. `SC4UIScale.log` from your Plugins folder.
3. The other mods you have installed — especially UI ones.
4. Whether it happens on the *first* open of a panel or every time. That
   distinction usually identifies the cause on its own.
