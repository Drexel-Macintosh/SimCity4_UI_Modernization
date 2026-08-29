Add SC4UIScale (`a-drexel`) and its `group-to-github` mapping

## What this adds

**SC4UIScale** — a UI scaling mod for SimCity 4. It enlarges the game's own
interface (toolbars, dialogs, menus, icons, fonts) so the UI stays readable at
modern resolutions, rather than upscaling the whole frame and blurring the city
view. The scale factor is picked from the resolution the game actually renders
at and can be changed in-game under Options → Graphic Options. Below 1320x900
the mod stays inert and the game behaves exactly as stock.

It is a code mod: the package installs `SC4UIScale.dll` at the Plugins root
(with a `withChecksum` entry, as required for DLLs), plus DBPF payload folders.

- Source and releases: https://github.com/Drexel-Macintosh/SimCity4_UI_Modernization
- Licence and third-party artwork attributions are in the repo.

## Why `lint-config.yaml` needs a line

Because the package ships a DLL, `lint.py` requires the release host to be a
known GitHub account for the group:

```
===> DLLs should be downloaded from the author's GitHub releases to ensure authenticity.
GitHub account "Drexel-Macintosh" for asset "a-drexel-sc4-ui-scale" is not known
to belong to group "a-drexel" (a new mapping needs to be defined in lint-config.yaml).
```

The DLL is released from **`github.com/Drexel-Macintosh/SimCity4_UI_Modernization`**,
which is my own account and repo — the same account opening this PR. So the added
mapping is:

```yaml
- a-drexel: Drexel-Macintosh
```

appended to `group-to-github`, mirroring what #164 did for `caspervg`.

## On the group name

`a-drexel` matches the naming convention `[a-z0-9]+(?:-[a-z0-9]+)*`
(`lint.py` line 256) and lint accepts it.

The leading `a-` is deliberate and load-bearing, not a typo or a bid for
alphabetical priority in listings. sc4pac orders files within a subfolder by
`<group>.<name>`, and this package installs into `050-load-first`. It **must**
load before CAM so that CAM's own files win per-TGI where they overlap — losing
to CAM is the compatibility mechanism. `a-drexel` sorts before `cam.*`; a plain
`drexel` does not, and would silently invert that precedence with no error
anywhere. I verified this with a per-TGI winner diff across 1888 keys: zero CAM
keys changed hands under the proposed layout. Happy to rename if you would
rather I solve the ordering another way, but it would need a different mechanism
rather than a straight rename.

## Verification

With this one-line change, a full-channel lint run including the new package file
is clean:

```
Successfully validated 693 files.
```

Without it, the same run exits 1 with the DLL-authenticity error quoted above.
