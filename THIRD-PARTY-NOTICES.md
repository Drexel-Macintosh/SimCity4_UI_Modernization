# Licences and notices

**This project's own code is CC0 1.0** — public domain, no rights reserved, no
attribution required. See `LICENSE`.

It statically links two libraries whose terms you must honour if you
redistribute a build.

| Component | Licence | Where |
|---|---|---|
| **[gzcom-dll](https://github.com/nsgomez/gzcom-dll)** — Nelson Gomez | **LGPL-2.1-or-later** | `vendor/gzcom-dll/` |
| **MinHook** — Tsuda Kageyu, 2009–2017 | **BSD-2-Clause** | `vendor/minhook/` |
| ↳ HDE (Hacker Disassembler Engine), embedded in MinHook | see per-file headers | `vendor/minhook/src/hde/` |

That is the complete list.

## gzcom-dll — LGPL-2.1-or-later

Compiled into `SC4UIScale.dll`. LGPL-2.1 §6 requires that recipients of a
binary be able to relink it against a modified version of the library. **This
repository satisfies that**: the library's full source is in `vendor/`, this
project's full source is here, and `docs/BUILDING.md` gives the build command.
Modifications to gzcom-dll itself, if any are ever made, remain LGPL.

Full text: `vendor/gzcom-dll/LICENSE`.

## MinHook — BSD-2-Clause

Redistribution in binary form must reproduce its copyright notice, conditions
and disclaimer. Full text: `vendor/minhook/LICENSE.txt`.

---

# Content notice — the packages in a Release download

The sections above cover **code**. This covers the **art**, and applies only to
the binary bundle attached to a Release. **This repository contains none of
it** — it ships the generators, and you build the packages against your own
installation.

## What the packages contain

Almost every `z_SC4UIScale_*.dat` is **enlarged copies of artwork already on
your disk**, produced by the scripts in `tools/`. For the art and the layout
scripts nothing is redrawn or recoloured: each entry is its 1× original
resampled, and each `.UI` script is its original with size and rect attributes
multiplied.

**Three exceptions, so "nothing is re-authored" is not read wider than it is:**

* **`WebText` is re-authored text**, not a resample — three of EA's own locale
  strings with the dead `SimCity.com` domain swapped for `Simtropolis.com`, so
  the visible text matches the DLL's web redirect
  (`tools/webtext/build_webtext.py`).
* **`CamGraphLabels` is a string we author**, not a copy of anything — see the
  table.
* **`font=` attributes are rewritten in every `.UI` script we emit** — a font
  NAME is replaced by the corresponding font GUID. Captions, colours and window
  flags are copied verbatim.

| Package | Derived from | Owner |
|---|---|---|
| `SelectiveArt`, `DialogStatic`, `ItemIcons`, `FontStyle-*` | SimCity 4 Deluxe's own archives | **Maxis / Electronic Arts** |
| `WebText` | three EA locale strings with the domain swapped (see above) | **Maxis / Electronic Arts** |
| `ItemIconsSub` | **mostly plugin artwork, not stock art.** 130 entries: **55 from memo33's Submenus DLL**, 69 from the Colossus Addon Mod's System Integration Module and from Maxis landmark-building plugins, 5 from Maxis *Buildings* `.SC4Lot` files, and **1** stock image (the Submenus DLL's "Missing Thumb", which ships in `SimCity_1.dat`) | **memo33**, **the CAM team**, **Maxis / Electronic Arts** |
| `NamIcons` | Network Addon Mod's menu icons | **the NAM team** |
| `CamUI` | Colossus Addon Mod's UI scripts and art — 9 scripts and 13 bitmaps as of v2.97.1, including the three dialogs CAM **adds** (its city info screen and its civic and school query panels) rather than replaces | **the CAM team** |
| `CamGraphLabels` | **not derived — authored by us.** One caption record at a resource id CAM's Power and Water charts bind but which exists in no installed file, leaving that legend row blank. CAM's files are never modified | **ours** (CC0), supplied for the Colossus Addon Mod |
| `WarriorUI` | *God Terraforming in Mayor Mode* | **warrior** |
| `SaveWarningUI` | *Save Warning* | **cyclone-boom** |
| `ThirdPartyUI` | *36 Slot Building Styles UI* — its `.UI` layout script and art | **CoriBoom**, whose file is packaged inside **null-45**'s *Allow More Building Styles* |

You must own SimCity 4 Deluxe for any of it to be meaningful.

**Which packages are gated, and which are not.** `CamUI`, `NamIcons`,
`ThirdPartyUI`, `SaveWarningUI` and `WarriorUI` are gated at load time on the
owning mod's file being present and deactivate themselves otherwise — those
five are the complete gate table in `src/ScaleTier.cpp`. **`ItemIconsSub` and
`CamGraphLabels` are not gated:** they load regardless. Their entries are keyed
to resource ids that only those plugins introduce, so without the plugin
nothing looks them up and they sit inert — inert, but not gated.

## Position

This is a **compatibility layer**, not a redistribution of anyone's mod. It
contains no gameplay data, no networks, no lots, no textures and no DLLs from
any project above — only enlarged UI imagery, the scripts that position it, and
the single caption record described in the table.
Where a mod is patched we enlarge **that mod's own artwork** rather than
substituting Maxis art, so what appears on screen is still that author's work.

**If you are one of these authors and would rather this were not distributed,
open an issue and the package is removed from the release.** No argument to be
had — it is your artwork.

The Maxis-derived packages are enlarged copies of game assets, useless without
a licensed copy of the game, distributed at no charge, in the same tradition as
two decades of SimCity 4 UI mods. If Electronic Arts would prefer otherwise,
the release assets come down on request; this repository stands on its own.

**This repository contains no EA artwork, sound or `.dat` data.** One exception
to "no game text", named rather than glossed: `tools/webtext/build_webtext.py`
hard-codes three of the game's own locale strings — the ones advertising the
dead `SimCity.com` — with the domain swapped, because the DLL redirects that
link and the visible text has to match. Those three short strings are quoted
for interoperability, are not licensed here, and fall under the same carve-out
as the derived art.

SimCity 4 is a trademark of Electronic Arts. This project is unofficial and has
no affiliation with or endorsement from EA or Maxis.
