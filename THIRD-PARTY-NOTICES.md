# Dependencies and third-party notices

**Short version:** this project's own code is public domain (CC0 1.0, no rights
reserved, no attribution required). It statically links **three** third-party
libraries whose terms you must honour if you redistribute a build:
**gzcom-dll** (LGPL-2.1-or-later), **MinHook** (BSD-2-Clause) and
**sc4-dll-utilities** (LGPL-2.1-or-later, the INI parser).

That is the complete list. Every claim below was read out of the files named,
in this tree, not taken from a package manifest or from memory.

---

## The whole dependency list

| # | Component | Licence | How it is used | Where |
|---|---|---|---|---|
| 1 | **gzcom-dll** — Nelson Gomez (`nsgomez`) | **LGPL-2.1-or-later** | **Statically compiled into `SC4UIScale.dll`** | `vendor\gzcom-dll\` |
| 2 | **MinHook** — Tsuda Kageyu, 2009-2017 | **BSD-2-Clause** | **Statically compiled into `SC4UIScale.dll`** | `vendor\minhook\` |
| 2a | ↳ **HDE** (Hacker Disassembler Engine), embedded in MinHook | see per-file headers | length-decoder used by MinHook | `vendor\minhook\src\hde\` |
| 3 | **sc4-dll-utilities** — Nicholas Hayes (`0xC0000054`) | **LGPL-2.1-or-later** | `IniReader`/`StringViewUtil` compiled in to parse `SC4UIScale.ini` and the shared `SC4GraphicsOptions.ini` (replaces `GetPrivateProfile*`) | `vendor\sc4-dll-utilities\` |

There is **nothing else compiled in**. In particular **no code** from any of
the following is used, linked or built into `SC4UIScale.dll`. These are the
other well-known SimCity 4 DLL projects and are listed here only so their
absence is on the record rather than assumed:

* `0xC0000054/sc4-resource-loading-hooks` — **no code used**
* any other `0xC0000054/sc4-*` plugin — **no code used**
* `memo33/*` (3d-camera, transparent-texture-fix, …) — **no code used**
* `nsgomez/scgl` — **no code used**

Verified by search across `src\` for each of those project names and authors:
**zero matches.** The only third-party code paths in the build are the three
rows above, and all are visible as explicit `<ClCompile>` entries in
`src\SC4UIScale.vcxproj`.

**Two things that statement does NOT cover, and must not be read as denying:**

* **memo33's Submenus DLL — its ARTWORK.** No code from it is used, but the
  `ItemIconsSub` package in a Release download contains enlarged copies of
  **55 of that mod's menu icons**. That is an art matter, covered in the
  CONTENT NOTICE at the bottom of this file, not a code dependency.
* **memo33's Submenus DLL — a source clone in the working tree.**
  `tools\research\submenus-dll-src\` is a full clone of
  <https://github.com/memo33/submenus-dll> (LGPL-3), kept as
  reverse-engineering reference material. Nothing from it is compiled;
  `src\SC4UIScale.vcxproj` lists no file from that tree. It is not part of the
  published source repository and not part of any Release download. Recorded
  in `NOTICE`, section 2.

---

## 1. gzcom-dll — LGPL-2.1-or-later

* Upstream: <https://github.com/nsgomez/gzcom-dll>
* Pinned commit: `08c529bc2edd32e11c269960a03011ad035c0529` (2026-07-12) — the
  git submodule at `vendor\gzcom-dll` (declared in `.gitmodules`)
* Licence text as vendored: `vendor\gzcom-dll\LICENSE`
* Upstream's own words: *"This project is licensed under the GNU Lesser
  General Public License, version 2.1 or (at your option) any later version…
  You may dynamically link it with proprietary software such as SimCity 4, but
  changes you make to gzcom-dll must also be shared under the LGPL v2.1
  license or later."*

**We link it STATICALLY, not dynamically.** Three of its translation units are
built directly into our DLL:

```
vendor\gzcom-dll\gzcom-dll\src\cRZBaseString.cpp
vendor\gzcom-dll\gzcom-dll\src\cRZBaseUnknown.cpp
vendor\gzcom-dll\gzcom-dll\src\cRZCOMDllDirector.cpp
```

Upstream's README addresses dynamic linking; it does not address static
linking, so the licence itself governs. What that means in practice:

* **LGPL-2.1 §6 applies to the combined binary.** A recipient of
  `SC4UIScale.dll` must be able to obtain the library's source and to relink
  the program against a modified version of the library. **Publishing this
  project's complete source, with the library provided at the exact pinned
  revision via the `vendor\gzcom-dll` git submodule, is what satisfies that**
  — and is the reason the source is published rather than only the binary.
* **§6 does NOT relicense our code.** LGPL-2.1 explicitly allows a "work that
  uses the Library" to carry terms of your choice. That is why the CC0
  dedication in `LICENSE` is compatible with this dependency, and why our code
  can be public domain while this library stays LGPL.
* **Modifications to gzcom-dll itself must be shared under LGPL-2.1 or later.**
  If you change anything under `vendor\gzcom-dll\`, that change is LGPL, not
  CC0, regardless of what `LICENSE` says.

> If you want a build with no copyleft dependency at all, the three files above
> are the only thing standing in the way. They are small, and the headers they
> sit behind are reverse-engineered game ABI declarations. Replacing them is a
> tractable piece of work — it just has not been done, and it is dishonest to
> imply otherwise.

## 2. MinHook — BSD-2-Clause

* Copyright (C) 2009-2017 Tsuda Kageyu. All rights reserved.
* Licence text as vendored: `vendor\minhook\LICENSE.txt`
* Pin: git submodule at `vendor\minhook`, upstream commit
  `d94c64d32ea37bc4f5ee47d580709f70c6fb6080` (verified byte-identical to the
  previously vendored sources)
* Statically compiled: `buffer.c`, `hook.c`, `trampoline.c`,
  `src\hde\hde32.c`, `src\hde\hde64.c`

BSD-2-Clause obligations, in full:

1. Redistributions of **source** must retain the copyright notice, the
   conditions and the disclaimer.
2. Redistributions in **binary** form must reproduce the copyright notice, the
   conditions and the disclaimer **in the documentation or other materials
   provided with the distribution** — which is what this file is.

No attribution in advertising is required, and there is no copyleft.

### 2a. HDE (embedded in MinHook)

MinHook embeds the Hacker Disassembler Engine to decode instruction lengths.
Those files carry their own copyright notices in their headers; see
`vendor\minhook\src\hde\`.

## 3. sc4-dll-utilities — LGPL-2.1-or-later

* Upstream: <https://github.com/0xC0000054/sc4-dll-utilities>
* Pinned commit: `cb52a04f2704893021b986f7619321cf63c653ba` — the git
  submodule at `vendor\sc4-dll-utilities` (declared in `.gitmodules`),
  byte-identical to the previously vendored subset.
* Licence text: `vendor\sc4-dll-utilities\LICENSE.txt` (upstream repo root).

**We link it STATICALLY, not dynamically.** Two files are built into our DLL:

```
vendor\sc4-dll-utilities\sc4-dll-utilities\include\IniReader.h      (header-only)
vendor\sc4-dll-utilities\sc4-dll-utilities\src\StringViewUtil.cpp
```

The same LGPL-2.1 §6 analysis as gzcom-dll applies: recipients of
`SC4UIScale.dll` must be able to obtain this library's source and relink;
publishing the complete source at the pinned submodule revision satisfies
that. Modifications under `vendor\sc4-dll-utilities\` are LGPL, not CC0.

It parses both INI files we read: our own `SC4UIScale.ini`
(`src\Settings.cpp`) and the shared `SC4GraphicsOptions.ini` owned by the
optional SC4GraphicsOptions plugin (`src\SC4UIScaleDllDirector.cpp`,
`src\UiSpike.cpp`). That plugin itself uses a different parsing library; we
do not stay bug-compatible with it, and a missing or malformed file falls
back to defaults exactly as with `GetPrivateProfile*`.

---

## 4. SimCity 4 itself — not ours, and not licensed here

SimCity 4 and all of its assets are the property of **Electronic Arts**. This
project is an unofficial, unaffiliated modification.

* **It contains no EA code**, and no EA artwork, sound or `.dat` data is copied
  into this repository or into the DLL.
* It **reads and patches the running game's memory**, and it **derives** scaled
  art packages and font configurations from the game's own resources. Those
  derived files are produced from a user's existing installation.
* Derived art and font files are **not** covered by the CC0 dedication and are
  **excluded from the published source**: the published source tree contains
  zero `.dat`, `.ui` and `.png` files.
* **One exception to "no game text in the repository", named rather than
  glossed:** `tools\webtext\build_webtext.py` hard-codes three of the game's
  own locale strings — the ones that advertise the dead `SimCity.com` — with
  the domain swapped, because the DLL redirects that link and the visible text
  has to match. That file is published, so three short EA-authored strings do
  travel with the source. They are quoted for interoperability; they are not
  licensed here and are covered by the same EA carve-out as the derived art.

Redistributing derived game art is a separate decision from licensing the
code, and this file does not make it. If you package a binary release that
bundles generated `.dat` art, that is a choice about EA's assets, not about
anything above.

---

## 5. Not a dependency, but present in the wider setup

Listed so the picture is complete; none of these is linked, vendored, or
redistributed by this project:

* **dgVoodoo2** — an optional third-party graphics wrapper the user installs
  separately to run SimCity 4 at a modern resolution. Not shipped here.

---

## 6. How to satisfy everything, in one paragraph

Ship the binary **with** a copy of this file and the three upstream licence
texts (`vendor\gzcom-dll\LICENSE`, `vendor\minhook\LICENSE.txt`,
`vendor\sc4-dll-utilities\LICENSE.txt`), and publish
or otherwise make available the complete corresponding source. That covers
MinHook's notice requirement and gzcom-dll's LGPL-2.1 §6 relink requirement at
the same time. Our own code asks for nothing.

*This file records facts about this tree and the intent of its authors. It is
not legal advice.*

---

# CONTENT NOTICE — the `.dat` packages in a RELEASE download

The sections above cover **code**. This one covers the **art**, and it applies
only to the binary bundle attached to a GitHub Release. **The source repository
contains none of it** — it ships the generators, and you build the packages
against your own installation.

## What the packages actually contain

Almost every `z_SC4UIScale_*.dat` is **enlarged copies of artwork and UI
scripts that are already on your disk**, produced by the scripts in `tools\`.
For the art and the layout scripts nothing is redrawn or recoloured: each entry
is its 1x original resampled to 1.5x, 2x or 3x, and each `.UI` script is its
original with size and rect attributes multiplied.

**Three exceptions, so that "nothing is re-authored" is not read wider than it
is:**

* **`WebText` is re-authored text, not a resample.** Its three entries are
  EA's own `SimCityLocale.DAT` strings with the dead `SimCity.com` domain
  swapped for `Simtropolis.com`, so the visible text matches the DLL's web
  redirect. The replacement strings are hard-coded in
  `tools\webtext\build_webtext.py`.
* **`CamGraphLabels` is a string we author**, not a copy of anything — see the
  table below.
* **`font=` attributes are rewritten in every `.UI` script we emit.** A font
  NAME is substituted for the corresponding font GUID
  (`tools\selective-safe\build_selective_safe.py`). Captions, colours and
  window flags are copied verbatim; only the form of the font reference
  changes.

| package | derived from | owner |
|---|---|---|
| `SelectiveArt`, `DialogStatic`, `ItemIcons` | SimCity 4 Deluxe's own archives | **Maxis / Electronic Arts** |
| `WebText` | three EA locale strings with the domain swapped (see above) | **Maxis / Electronic Arts** |
| `ItemIconsSub` | **mostly plugin artwork, not stock art.** 130 entries: **55 from memo33's Submenus DLL**, 69 from the Colossus Addon Mod's System Integration Module and from Maxis landmark-building plugins, 5 from Maxis *Buildings* `.SC4Lot` files, and **1** stock image — the Submenus DLL's "Missing Thumb", which ships in `SimCity_1.dat`. Source: `tools\itemicons\build_itemicons_sub.py` | **memo33**, **the CAM team**, **Maxis / Electronic Arts** |
| `CamUI` | Colossus Addon Mod's UI scripts + art — **9 scripts and 13 bitmaps** as of v2.97.1: the six stock dialogs CAM replaces, CAM's **own** city info screen and its civic + school query panels, and the strips, badges and splash they draw | **the CAM team** |
| `CamGraphLabels` | **not derived — authored by us.** One 20-byte caption record at a resource id CAM's Power and Water chart exemplars bind but which exists in no installed file, so that row draws with no caption. The word matches CAM's own `Exported` label with its trailing CRLF omitted. CAM's files are never modified. | **ours** (CC0), supplied for the Colossus Addon Mod |
| `NamIcons` | Network Addon Mod's menu ItemIcons (392) | **the NAM team** |
| `WarriorUI` | *God Terraforming in Mayor Mode* scripts + art | **warrior** |
| `SaveWarningUI` | *Save Warning*'s dialog scripts | **cyclone-boom** |
| `ThirdPartyUI` | *36 Slot Building Styles UI* — its `.UI` layout script and art | **CoriBoom**, whose file is packaged inside **null-45**'s *Allow More Building Styles* |
| `FontStyle-*.ini` | the game's own font table, rescaled | **Maxis / Electronic Arts** |

**You must own SimCity 4 Deluxe for any of it to be meaningful.**

**Which packages are gated, and which are not.** Five packages — `CamUI`,
`NamIcons`, `ThirdPartyUI`, `SaveWarningUI` and `WarriorUI` — are gated at load
time on the owning mod's file being present, and deactivate themselves
otherwise. The gate table is `kThirdPartyDeps` in `src\ScaleTier.cpp`; those
five rows are its complete contents. **Two packages that carry third-party
artwork are NOT gated**, and are named here rather than covered by a general
claim:

* **`ItemIconsSub` has no gate row.** It loads whether or not the Submenus DLL,
  CAM or the landmark plugins are installed. Its entries are keyed to resource
  ids those plugins introduce, so with the plugin removed nothing looks them up
  and they are inert — but that is inertness, not a gate.
* **`CamGraphLabels` has no gate row.** It supplies one resource id that only
  CAM's chart exemplars bind, so it is likewise inert without CAM.

## Position, stated plainly

* This is a **compatibility layer**, not a redistribution of anyone's mod. It
  contains no gameplay data, no networks, no lots, no textures, no DLLs from
  any of the projects above — only enlarged UI imagery, the UI scripts that
  position it, and the single caption record described in the table above.
* Enlarging a mod's own icons is what makes that mod usable at high DPI. We
  deliberately upscale **each mod's own artwork** rather than substituting
  Maxis art, so what you see on screen is still that author's work.
* Overrides are documented in `tools\research\UPSTREAM-*-REPORT.md`, written
  to be readable by the mod's author: what we touch, why, and what we do
  **not** touch. There are five — CAM, NAM, *36 Slot Building Styles UI*,
  *Save Warning* and *God Terraforming in Mayor Mode*. **There is no report
  for memo33's Submenus DLL**, whose 55 icons `ItemIconsSub` enlarges; that
  override is recorded only here.
* **For the scaling work, no defect is claimed in any of these mods.** In
  every scaling case the symptom was ours — our layer doubled a container and
  their correctly-authored 1x art ended up inside it.
* **One exception, stated rather than buried.** `tools\research\UPSTREAM-CAM-REPORT.md`
  *does* report data defects in CAM / the SIM package — a chart caption id
  that resolves in no installed file (which is why `CamGraphLabels` exists),
  submenu parents pointing at ids no plugin defines, and icon ids with no art
  anywhere. Those are reproducible without any of our packages installed, are
  reported upstream, and we work around them by ADDING a resource, never by
  editing CAM's files.

## If you are one of these authors and would rather we did not

Open an issue and the package will be removed from the Release. There is no
argument to have: it is your artwork. The layer is built so that removing one
package degrades gracefully — that mod's UI simply renders at 1x again, and
nothing else changes.

## For Maxis / Electronic Arts material

The Maxis-derived packages are enlarged copies of game assets, useless without
a licensed copy of SimCity 4 Deluxe, distributed at no charge, in the same
tradition as two decades of SC4 UI mods. If EA would prefer they not be
distributed, the Release assets come down on request and the source repository
— which contains no EA content of any kind — continues to stand on its own.
