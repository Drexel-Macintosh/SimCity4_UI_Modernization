#!/usr/bin/env python3
r"""Where SimCity 4 lives on THIS machine - resolved, never hard-coded.

WHY THIS EXISTS (task #108, 2026-08-05). Twenty-odd scripts in this repo each
carried their own literal
    C:\Users\<someone>\OneDrive\Documents\SimCity 4\Plugins
which is three separate problems in one string: it publishes a username, it
assumes OneDrive has redirected Documents, and it assumes a Steam default
install. Every one of them had to be edited by hand before the repo could be
published, and the twenty-first would have been written the same way.

    from sc4paths import plugins_dir, game_dir, apps_dir

RESOLUTION ORDER, most explicit first:

    plugins_dir()   $SC4_PLUGINS
                    -> <Documents>\SimCity 4\Plugins        (Windows shell API)
                    -> %USERPROFILE%\OneDrive\Documents\...  (redirected)
                    -> %USERPROFILE%\Documents\...           (not redirected)

    game_dir()      $SC4_GAME_DIR
                    -> the Steam default
                    -> the retail/EA default

`Documents` IS NOT `%USERPROFILE%\Documents` ON EVERY MACHINE. OneDrive's
"back up your folders" moves it, and SC4 follows the shell's idea of My
Documents, not the literal path. Both are tried, and the one that EXISTS wins -
guessing wrong here produces an empty scan, which reads as "nothing found"
rather than as an error. That failure mode has already cost this project twice
(the #140 splash and the #139 icon census both turned a bad read into a
confident negative), so `plugins_dir(require=True)` raises instead.
"""
import os

_STEAM = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
_RETAIL = r"C:\Program Files (x86)\Maxis\SimCity 4 Deluxe"


def _first_dir(paths):
    for p in paths:
        if p and os.path.isdir(p):
            return p
    return None


def _documents_candidates():
    """Every plausible My Documents, most authoritative first."""
    out = []
    try:                                    # the shell's own answer
        import ctypes.wintypes
        buf = ctypes.create_unicode_buffer(260)
        # CSIDL_PERSONAL = 5, SHGFP_TYPE_CURRENT = 0
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            out.append(buf.value)
    except Exception:
        pass
    home = os.path.expanduser("~")
    out.append(os.path.join(home, "OneDrive", "Documents"))
    out.append(os.path.join(home, "Documents"))
    return out


def user_sc4_dir(require=False):
    """<Documents>\\SimCity 4 - the per-user game folder."""
    hit = _first_dir(os.path.join(d, "SimCity 4") for d in _documents_candidates())
    if hit is None and require:
        raise SystemExit(
            "could not find <Documents>\\SimCity 4. Set SC4_PLUGINS to your "
            "Plugins folder, or SC4_GAME_DIR to the install root.")
    return hit


def plugins_dir(require=False):
    """The USER Plugins folder (<Documents>\\SimCity 4\\Plugins).

    This is only ONE of the two trees SC4 loads - the install also has
    <game>\\Plugins, and both are scanned RECURSIVELY. Any census that claims
    coverage must walk both; see REGRESSION.md, 2026-08-05.
    """
    env = os.environ.get("SC4_PLUGINS")
    if env:
        return env
    base = user_sc4_dir(require=require)
    if base is None:
        return None
    p = os.path.join(base, "Plugins")
    if require and not os.path.isdir(p):
        raise SystemExit("no Plugins folder under %s - set SC4_PLUGINS." % base)
    return p


def game_dir(require=False):
    """The install root (the folder holding SimCity_1.dat ... and Apps\\)."""
    env = os.environ.get("SC4_GAME_DIR")
    if env:
        return env
    hit = _first_dir([_STEAM, _RETAIL])
    if hit is None and require:
        raise SystemExit(
            "could not find the SimCity 4 Deluxe install. Set SC4_GAME_DIR.")
    return hit


def apps_dir(require=False):
    """<game>\\Apps - where SimCity 4.exe and the install-root FontStyle live."""
    g = game_dir(require=require)
    return None if g is None else os.path.join(g, "Apps")


def game_plugins_dir(require=False):
    """<game>\\Plugins - the INSTALL-side plugin tree, the one that gets
    forgotten. A "stock" claim that only cleared the user tree is not stock."""
    g = game_dir(require=require)
    return None if g is None else os.path.join(g, "Plugins")


def exe_path(require=False):
    a = apps_dir(require=require)
    return None if a is None else os.path.join(a, "SimCity 4.exe")


if __name__ == "__main__":
    for fn in (user_sc4_dir, plugins_dir, game_dir, apps_dir,
               game_plugins_dir, exe_path):
        print("%-18s %s" % (fn.__name__ + "()", fn()))
