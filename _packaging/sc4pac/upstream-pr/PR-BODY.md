This adds **SC4UIScale** (SimCity 4 UI Modernization) — two packages under a
new group `a-drexel` — together with the group's `group-to-github` mapping in
`lint-config.yaml`, following the single-PR precedent of #164.

## What the mod is

A DLL mod for SimCity 4 Deluxe **1.1.641 (Windows digital edition)** that
enlarges the game's own interface — toolbars, dialogs, menus, icons and fonts —
by 1.5x/2x/3x on high-resolution displays, rather than upscaling the whole
frame and blurring the city view. The factor is picked from the resolution the
game actually renders at and can be changed in-game under Options → Graphic
Options. Below 1440x1080 it stays inert and the game behaves exactly as stock.

- Source and releases: https://github.com/Drexel-Macintosh/SimCity4_UI_Modernization
- Licence and third-party artwork attributions are in the repo, and
  `THIRD-PARTY-NOTICES.md` also installs inside the overrides package.

## The two packages (one shared asset)

- **`a-drexel:sc4-ui-scale`** (`050-load-first`): `SC4UIScale.dll` at the
  Plugins root (with a `withChecksum` entry, as required for DLLs) plus
  stock-derived art/font packages in `010-SC4UIScale/`.
- **`a-drexel:sc4-ui-scale-mod-overrides`** (`900-overrides`): enlarged copies
  of other mods' own UI artwork (CAM, NAM, Save Warning, 36 Slot Building
  Styles, God Terraforming, Carbon Skin), gated at runtime on those mods'
  files rather than declared as dependencies — the gates must also fire for
  hand-installed copies, and a hard dependency would drag this package along
  when e.g. CAM is uninstalled.

## Two deliberate deviations a reviewer will notice

**The group name and subfolder are load-bearing.** sc4pac orders files within
a subfolder by `<group>.<name>`, and the early package must load **before**
CAM so that CAM's own files win per-TGI where they overlap — losing to CAM is
the compatibility mechanism, which is why the package sits in `050-load-first`
rather than `150-mods`, and why the group is `a-drexel` (sorts before `cam.*`)
rather than `drexel`. Verified with a per-TGI winner diff across 1888 keys:
zero CAM keys changed hands. Happy to solve the ordering another way if you
prefer, but a straight rename would silently invert CAM precedence.

**The DLL rewrites its own installed files at boot.** Each art package is a
stable `z_SC4UIScale_<Pkg>.dat` plus inert `.uipay` payload files; at boot the
DLL copies the payload matching the player's resolution over the stable
`.dat`. Filenames never change, so update/uninstall remove exactly the names
that were installed. This relies on sc4pac verifying checksums at install
time (in staging) and not tracking post-install content — measured against
sc4pac 0.10.0. The DLL also writes `SC4UIScale.ini` at the Plugins root on
first launch (an ini inside the versioned package folder would be deleted by
every update); the file survives uninstall, and the package description says
so.

## Why `lint-config.yaml` needs a line

Because the package ships a DLL, `lint.py` requires the release host to be a
known GitHub account for the group:

```
GitHub account "Drexel-Macintosh" for asset "a-drexel-sc4-ui-scale" is not known
to belong to group "a-drexel" (a new mapping needs to be defined in lint-config.yaml).
```

The DLL is released from `github.com/Drexel-Macintosh/SimCity4_UI_Modernization`,
the same account opening this PR, so the added mapping is:

```yaml
- a-drexel: Drexel-Macintosh
```

## Verification

- Full-channel `lint.py` including this package: `Successfully validated 693
  files.` Positive control: with the mapping removed, the same run exits 1
  with the DLL-authenticity error quoted above.
- All ~85 `withChecksum` entries are generated from the built release bundle
  and re-verified against the published zip.
- Install/uninstall exercised end-to-end against sc4pac 0.10.0 (local channel
  + the real GitHub asset), plus an in-game boot verification at 2x.

Note: CI on the previous submission (#199) died in `actions/checkout` on the
new `pull_request_target` fork policy (`allow-unsafe-pr-checkout`) before lint
ran — fork PRs may need a workflow tweak on your side.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
