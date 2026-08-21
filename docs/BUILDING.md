# Building

Two independent things: the **DLL**, and the **art packages**. You can build
either without the other.

## The DLL

Needs MSVC (VS 2022 or later) with the v143 toolset and a Windows 10 SDK.
It targets **Win32** — SimCity 4 is a 32-bit process.

```
msbuild src\SC4UIScale.vcxproj -p:Configuration=Release -p:Platform=Win32
```

Output: `build\Release\SC4UIScale.dll`. Copy it into
`Documents\SimCity 4\Plugins\` beside `SC4UIScale.ini`.

`vendor\` carries gzcom-dll and MinHook as **git submodules**; both are compiled
in. Clone with `--recursive`, or run `git submodule update --init` after a plain
clone, before building:

```
git clone --recursive <repo-url>
# or, after a plain clone:
git submodule update --init
```

`SC4UIScale.sln` opens in Visual Studio if you prefer.

> `/PDBALTPATH:%_PDB%` and `/d1trimfile` are set deliberately — without them the
> compiler writes your absolute build path into the binary, as ASCII *and* as a
> UTF-16 string in `.rdata`. Keep them.

## The art packages

**The `.dat` packages are not in this repository.** They are enlarged copies of
artwork from your own SimCity 4 installation, so you generate them locally.
(The [Releases](../../releases) page has prebuilt ones if you just want to play.)

You need **Python 3.10+** and **Pillow**, plus **.NET** to compile the two
helper tools.

```
# 1. helper tools (once)
csc tools\dbpf\DbpfExtract.cs
csc tools\dbpf\DbpfPack.cs
csc tools\upscale\Upscale2x.cs

# 2. point the scripts at your install (optional - they auto-detect
#    a Steam install and a redirected Documents folder)
set SC4_GAME_DIR=C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe
set SC4_PLUGINS=%USERPROFILE%\Documents\SimCity 4\Plugins

# 3. extract the 1x source art from your own archives
python tools\dbpf\find_tgi.py <instance-id>      # locate a resource
DbpfExtract.exe "<archive>.dat" out 0x856DDBAC   # pull art out

# 4. build the packages
python tools\selective-safe\build_selective_safe.py    # main UI art
python tools\dialog-static\build_dialog_static.py      # static dialogs
python tools\itemicons\stage_icons.py                  # menu icons
python tools\fonts\make_fontstyle.py                   # font tables
```

Each builder takes a scale factor and writes a `z_SC4UIScale_*.dat`. Deploy
those to `Documents\SimCity 4\Plugins\`, with the third-party ones in the
`zzz-SC4UIScale\` subfolder.

### Three rules that are not optional

**A mod's own dialogs are not in the game's data, so nothing here can build
them from a stock source.** The dialog builder reads
`tools\dialog-static\thirdparty-src\` for those, and that folder is **not
shipped** — it holds verbatim extracts of other people's mods. Extract them
yourself with `DbpfExtract.exe` from the mod you have installed, at the version
you have installed; the builder lists exactly which TGIs it wants and fails
loudly naming any that are missing. Without them, everything else still builds
and those dialogs simply stay unscaled.

**Load order decides everything.** SimCity 4 loads root `Plugins` files
*before* subfolders, and the last file loaded wins. A package that has to beat
another mod must live in a subfolder sorting after it — hence `zzz-`. Coverage
means *this package loads last for that resource*, not *the resource sits in
one of these files*. Those two are not the same question, and they disagree for
exactly one icon out of 392.

**Art the game cuts into cells must keep dividing evenly.** SimCity picks a
cell with an integer divide, and the divisor is compiled into the game:
`imageWidth ÷ 4` for a button's four-state strip (normal, hover, pressed,
disabled), and `÷ 3` on each axis for a nine-slice border. A scaled dimension
must stay a multiple of that number — snapped, not rounded. `356 × 1.5 = 534`,
and `534 ÷ 4 = 133.5`, which smears every state.

This is the whole reason the upscaler snaps dimensions at fractional factors
rather than just multiplying. At 2× and 3× it is free: an integer factor keeps
a multiple of 4 a multiple of 4. At 1.5× it is not — roughly a third of
nine-slice dimensions and **two fifths of strip widths** stop dividing evenly,
and each one shows up as a bright seam where a cell bleeds into its neighbour.

> This is not a menu-icon rule. It applies to every sheet the game
> cell-divides, in every builder. A new generator snaps too.

## Layout

```
src/       the plugin
vendor/    gzcom-dll (LGPL-2.1) + MinHook (BSD-2) - git submodules, compiled in
tools/     the package generators
docs/      these documents
```

## Two scalers, and which one to reach for

Geometry is scaled in two places, and they answer different questions.

**`ScaleSubtree` (`src/UiSpike.cpp`) is edge-derived:**

```
newW = ScaleRound(l + w, f) - ScaleRound(l, f)
```

That is deliberate. It means two panels that are flush before scaling are still
flush after it — round the width directly and abutting edges drift apart at a
non-integer factor, which shows up as bright seams between panel pieces.

It also means the scaled **size depends on the position**. At f = 1.5, `l * 1.5`
is a whole number only when `l` is even, so a control at an odd `l` comes out one
pixel narrower than the same control at an even `l`. If its art cell was built
for the wider one, the uncovered column and row draw as a thin "reverse L".

So **leaf** windows (`GetChildCount() == 0` — discrete icons, nothing butted
against them) are sized directly instead: `ScaleRound(w, f)`. Containers keep
the edge-derived rule. Both are no-ops at an integer factor, because
`ScaleRound(l * 2)` is exact for every `l`.

### Why the fix does not belong anywhere else

Two other levers reach the same arithmetic and cost more than they buy:

- **Moving the control** onto an even edge works, and shifts it by up to 2px at
  1.5×. That shift is invisible on a flyout with five well-spaced buttons and
  obvious in a 21-icon grid. Judge a positional change in the densest layout it
  touches.
- **Resizing the art** to match the window works arithmetically and is
  unbounded in practice: some windows are **created at runtime and appear in no
  `.UI` file**, yet they bind art by TGI like everything else. A builder can
  enumerate the scripted consumers of a sheet; it cannot enumerate the others.

Editing geometry in a `.UI` is scoped to that `.UI`. Editing art is scoped to
the whole game.
