#!/usr/bin/env python
"""Gate: the SELECTOR STATE MACHINE's derivation rule.

WHY THIS EXISTS
---------------
The Graphic Options selector grew feature-by-feature into a ~1,400-line
per-tick function whose defects were all of one shape: two sources of truth
disagreeing (shown-vs-full index, settings-vs-ini, staged-vs-pushed), or a
list mutated at a moment the player was using it. The v3.14 rewrite replaces
that with ONE pure function - SelDerive(state) -> UI - and this gate IS that
function's specification: it was written before the C++ and the C++ mirrors
it, not the other way around.

⚠ THIS MIRRORS THE RULE, IT DOES NOT CALL THE C++ - same declared limitation
as Test-BootStateValidate. The structural half (writes only at close, no
syscalls in the tick path) is Test-SelectorContract; the runtime half is a
launch.

THE CENTRAL DESIGN DECISION THE ROWS PIN DOWN: the player's scale pick is a
REQUEST that is never overwritten; the EFFECTIVE row is derived fresh every
pass as `request if usable else Auto`. Bounce and un-bounce then need no
state machine at all - stage a small resolution and the effective row falls
to Auto, stage the old resolution back and the original request simply fits
again. The audit finding "the bounce never undoes" is closed by construction.

PASS = exit 0.
"""
import sys

# ---- mirrors of ScaleTier.cpp (same tables as Test-BootStateValidate) ----
TIER_MIN = {1.5: (1440, 1080), 2.0: (1920, 1440),
            3.0: (2880, 2160), 4.0: (3840, 2880)}
INSTALLED = [1.5, 2.0, 3.0]

# scale rows, fixed order - row index is the combo index
SCALE_ROWS = [("Auto", None), ("1x", 1.0), ("1.5x", 1.5),
              ("2x", 2.0), ("3x", 3.0)]

MODE_B, MODE_F, MODE_W = 0, 1, 2      # Borderless, Fullscreen, Windowed
MODE_NAMES = ["Borderless", "Fullscreen", "Windowed"]


def fits(f, w, h):
    if f is None or f <= 1.01:
        return True
    if w <= 0 or h <= 0:
        return True          # unmeasured is not evidence of a small screen
    mw, mh = TIER_MIN.get(f, (10**9, 10**9))
    return w >= mw and h >= mh


def decide(w, h):
    for t in sorted(INSTALLED, reverse=True):
        if fits(t, w, h):
            return t
    return 1.0


# ---- the state ------------------------------------------------------------
class S(object):
    """Everything SelDerive is allowed to read. Nothing else exists."""
    def __init__(self, **kw):
        # session facts
        self.cap = (2400, 1600)          # panel max mode
        self.desk = (2400, 1600)         # registry desktop mode
        self.modes = [(800, 600), (1024, 768), (1280, 960), (1440, 1080),
                      (1600, 1200), (1920, 1440), (2048, 1536), (2400, 1600)]
        self.dll = True                  # SC4GraphicsOptions.dll present
        # visit facts (read once per open)
        self.live = (2400, 1600)         # measured render size
        self.live_mode = MODE_F          # mode the game is running in
        self.ini_mode = MODE_F           # SC4GraphicsOptions.ini
        self.ini_res = (2400, 1600)
        self.auto = True                 # our ini
        self.factor = 1.5
        # the player's staged requests (this visit; -1 = untouched)
        self.s_mode = -1
        self.s_res = -1                  # index into the FULL res list
        self.s_scale = -1                # scale row REQUEST, never overwritten
        for k, v in kw.items():
            setattr(self, k, v)


# ---- the pure function ----------------------------------------------------
def res_rows(st, eff_mode):
    """The FULL list for a mode. One index space - the UI shows exactly this."""
    if eff_mode == MODE_B:
        return [st.desk]                 # the desktop, and only that
    cap = st.cap if eff_mode == MODE_F else st.desk
    rows = [m for m in st.modes if m[0] <= cap[0] and m[1] <= cap[1]]
    if eff_mode == MODE_W:
        # A desktop-sized WINDOW overflows the screen the moment its title
        # bar exists - "fill the screen with a window" is Borderless's job.
        # (v3.13.2 also measured the C++ had NO windowed branch at all -
        # zero rows - which this rule now pins against.)
        rows = [m for m in rows if m != st.desk]
    return rows


def derive(st):
    """SelDerive: state -> the entire UI. Pure; no hidden reads."""
    # -- the pending future already in the files ---------------------------
    # In F/W the game renders the requested size, so ini != live means a
    # restart-pending change (an earlier Accept, or a hand edit - same
    # thing). In B the ini size is documented-ignored, so only the MODE can
    # be pending.
    pending = (st.ini_mode != st.live_mode) or (
        st.ini_mode != MODE_B and st.ini_res != st.live)

    base_mode = st.ini_mode if pending else st.live_mode
    eff_mode = st.s_mode if st.s_mode >= 0 else base_mode

    rows = res_rows(st, eff_mode)

    # -- effective resolution ---------------------------------------------
    if eff_mode == MODE_B:
        eff_res, res_sel = st.desk, 0
    else:
        if st.s_res >= 0 and st.s_res < len(rows):
            res_sel = st.s_res
        else:
            base = st.ini_res if (pending and st.ini_mode == eff_mode) \
                else st.live
            res_sel = rows.index(base) if base in rows else \
                (len(rows) - 1 if rows else -1)   # largest the mode offers
        eff_res = rows[res_sel] if res_sel >= 0 else (0, 0)

    # -- scale: request never overwritten, effective derived ---------------
    ini_row = 0 if st.auto else next(
        (i for i, (_, f) in enumerate(SCALE_ROWS)
         if f is not None and abs(f - st.factor) <= 0.01), 0)
    request = st.s_scale if st.s_scale >= 0 else ini_row
    usable = [f is None or f <= 1.01 or fits(f, *eff_res)
              for _, f in SCALE_ROWS]
    eff_scale = request if usable[request] else 0    # bounce is DERIVED

    # -- captions -----------------------------------------------------------
    def tag_res(i):
        m = rows[i]
        if eff_mode != MODE_B and m == st.live and st.live_mode == eff_mode:
            return "%dx%d (current)" % m
        if i == res_sel and (st.s_res >= 0 or pending):
            return "%dx%d - on restart" % m
        return "%dx%d" % m

    def tag_mode(m):
        name = MODE_NAMES[m]
        if m == st.live_mode:
            return name + " (current)"
        if m == eff_mode and (st.s_mode >= 0 or pending):
            return name + " - on restart"
        if m == MODE_B:
            return name + " (recommended)"
        return name

    def tag_scale(k):
        name, f = SCALE_ROWS[k]
        if not usable[k]:
            mw, mh = TIER_MIN[f]
            return "%s - needs %dx%d" % (name, mw, mh)
        if k == eff_scale:
            return "%s @ %dx%d" % (name, eff_res[0], eff_res[1])
        return name

    ui = {
        "mode_rows": [tag_mode(m) for m in range(3)] if st.dll else None,
        "mode_sel": eff_mode if st.dll else None,
        "res_rows": [tag_res(i) for i in range(len(rows))] if st.dll else None,
        "res_sel": res_sel if st.dll else None,
        "scale_rows": [tag_scale(k) for k in range(len(SCALE_ROWS))],
        "scale_sel": eff_scale,
        "eff_res": eff_res if st.dll else st.live,
        "eff_mode": eff_mode,
    }
    return ui


def commit(st):
    """What Accept writes. Returns a dict of writes; {} = nothing changed."""
    ui = derive(st)
    out = {}
    # scale - only if it changed against our ini
    row = ui["scale_sel"]
    want_auto = (row == 0)
    want_factor = SCALE_ROWS[row][1] if row > 0 else None
    ini_row = 0 if st.auto else next(
        (i for i, (_, f) in enumerate(SCALE_ROWS)
         if f is not None and abs(f - st.factor) <= 0.01), 0)
    if row != ini_row:
        out["AutoScale"] = 1 if want_auto else 0
        if not want_auto:
            out["ScaleFactor"] = want_factor
        if row != 1:
            out["ScaleAll"] = 1
    # mode+res - the PAIR, only if either changed against the gfx ini
    if st.dll:
        em, er = ui["eff_mode"], ui["eff_res"]
        if em != st.ini_mode or (em != MODE_B and er != st.ini_res):
            out["WindowMode"] = MODE_NAMES[em]
            out["WindowWidth"], out["WindowHeight"] = er
            out["dgExclusive"] = (em == MODE_F)
    return out


# ==== the rows =============================================================
FAILURES = []
CHECKS = [0]


def check(name, cond, detail=""):
    CHECKS[0] += 1
    print("  [%s] %s" % ("ok  " if cond else "FAIL", name))
    if not cond:
        FAILURES.append(name + (" - " + detail if detail else ""))


def main():
    print("Test-SelectorDerive")
    print("  mirrors the v3.14 SelDerive rule (see the docstring caveat)")
    print()

    # ---- truth-table transitions ----------------------------------------
    st = S()
    ui = derive(st)
    check("untouched open: fullscreen current, AutoScale shows as Auto",
          ui["mode_sel"] == MODE_F and ui["scale_sel"] == 0
          and ui["res_rows"][ui["res_sel"]] == "2400x1600 (current)"
          and commit(st) == {}, str(ui))

    st = S(s_scale=4)                      # pick 3x at 2400x1600
    ui = derive(st)
    check("3x picked on a screen that cannot carry it bounces to Auto",
          ui["scale_sel"] == 0 and "needs 2880x2160" in ui["scale_rows"][4])

    st = S(s_scale=3)                      # pick 2x at 2400x1600 - fits
    ui = derive(st)
    check("2x picked and it fits: effective 2x, caption names the future",
          ui["scale_sel"] == 3 and ui["scale_rows"][3] == "2x @ 2400x1600")

    st = S(s_scale=3, s_res=1)             # then stage 1024x768
    ui = derive(st)
    check("small res staged under a 2x pick: scale bounces to Auto",
          ui["scale_sel"] == 0 and ui["eff_res"] == (1024, 768))

    st = S(s_scale=3, s_res=7)             # res back to 2400x1600
    ui = derive(st)
    check("res staged BACK: the 2x request un-bounces by construction",
          ui["scale_sel"] == 3, str(ui))

    st = S(s_mode=MODE_B, s_res=1)         # borderless ignores the size
    ui = derive(st)
    check("borderless: one res row (the desktop), eff res = desktop",
          ui["res_rows"] == ["2400x1600 - on restart"]
          and ui["eff_res"] == (2400, 1600))

    st = S(s_mode=MODE_W)
    ui = derive(st)
    check("windowed staged: mode tagged on-restart, current stays marked",
          ui["mode_rows"][MODE_W] == "Windowed - on restart"
          and ui["mode_rows"][MODE_F] == "Fullscreen (current)")
    check("windowed offers rows, none of them desktop-sized, largest wins",
          len(ui["res_rows"]) > 0
          and all(not r.startswith("2400x1600") for r in ui["res_rows"])
          and ui["res_rows"][ui["res_sel"]].startswith("2048x1536"), str(ui))

    st = S(dll=False, s_scale=2)
    ui = derive(st)
    check("no SC4GraphicsOptions.dll: mode/res gone, scale intact",
          ui["mode_rows"] is None and ui["res_rows"] is None
          and ui["scale_sel"] == 2)

    st = S(live=(1024, 768), cap=(2400, 1600), desk=(2400, 1600),
           ini_res=(1024, 768))
    ui = derive(st)
    check("running small in fullscreen: the LIST still offers the panel",
          "2400x1600" in [r.split(" ")[0] for r in ui["res_rows"]]
          and ui["res_rows"][ui["res_sel"]] == "1024x768 (current)")

    st = S(ini_res=(1024, 768))            # accepted earlier, not restarted
    ui = derive(st)
    check("reopen after Accept: the ini future is shown, tagged on-restart",
          ui["res_rows"][ui["res_sel"]] == "1024x768 - on restart")

    st = S(ini_mode=MODE_W, ini_res=(1600, 1200))
    ui = derive(st)
    check("pending MODE change: dialog opens on the future, both tagged",
          ui["mode_sel"] == MODE_W
          and ui["mode_rows"][MODE_W] == "Windowed - on restart"
          and ui["res_rows"][ui["res_sel"]] == "1600x1200 - on restart")

    st = S(s_res=1, s_scale=2)             # 1024x768 + 1.5x in one visit
    w = commit(st)
    check("1024x768 + 1.5x, ini already Auto: only the res pair is written",
          "AutoScale" not in w and w.get("WindowWidth") == 1024, str(w))

    st = S(auto=False, factor=2.0, s_res=1)  # manual 2x ini, then small res
    w = commit(st)
    check("manual-2x ini + small res: the bounce IS written (AutoScale=1)",
          w.get("AutoScale") == 1 and w.get("WindowWidth") == 1024, str(w))

    st = S(s_scale=1)                      # pick 1x
    w = commit(st)
    check("manual 1x commit: ScaleAll untouched (reference-capture rule)",
          w.get("AutoScale") == 0 and "ScaleAll" not in w, str(w))

    st = S(s_mode=MODE_F, s_res=0)         # 800x600 exclusive
    w = commit(st)
    check("fullscreen 800x600: pair written, dgVoodoo exclusive on",
          w.get("WindowWidth") == 800 and w.get("dgExclusive") is True)

    st = S(s_mode=MODE_W)
    w = commit(st)
    check("windowed commit: dgVoodoo exclusive OFF rides along",
          w.get("dgExclusive") is False)

    # ---- swept invariants ------------------------------------------------
    print()
    bad = {k: 0 for k in ("I1", "I2", "I3", "I4", "I5", "I6")}
    desks = [(2400, 1600), (1920, 1080), (3840, 2160), (1024, 768)]
    for desk in desks:
        modes = [m for m in [(800, 600), (1024, 768), (1440, 1080),
                             (1600, 1200), (1920, 1440), (2400, 1600),
                             (2880, 2160), (3840, 2160)]
                 if m[0] <= desk[0] * 2]          # panels can exceed desktop
        for live_mode in (MODE_B, MODE_F, MODE_W):
            live = desk if live_mode == MODE_B else modes[-1]
            for ini_mode in (MODE_B, MODE_F, MODE_W):
                for ini_res in (live, (1024, 768)):
                    for auto, factor in ((True, 1.5), (False, 1.0),
                                         (False, 2.0), (False, 3.0)):
                        for s_mode in (-1, MODE_B, MODE_F, MODE_W):
                            for s_scale in (-1, 0, 2, 4):
                                st = S(desk=desk, cap=modes[-1], modes=modes,
                                       live=live, live_mode=live_mode,
                                       ini_mode=ini_mode, ini_res=ini_res,
                                       auto=auto, factor=factor,
                                       s_mode=s_mode, s_scale=s_scale)
                                rows = res_rows(st, derive(st)["eff_mode"])
                                for s_res in (-1, 0, len(rows) - 1):
                                    st.s_res = s_res
                                    ui = derive(st)
                                    # I1 selections exist in their lists
                                    if not (0 <= ui["scale_sel"] < 5) or (
                                            ui["res_rows"] is not None
                                            and not (0 <= ui["res_sel"]
                                                     < len(ui["res_rows"]))):
                                        bad["I1"] += 1
                                    # I2 the selected scale is always usable
                                    f = SCALE_ROWS[ui["scale_sel"]][1]
                                    if not fits(f, *ui["eff_res"]):
                                        bad["I2"] += 1
                                    # I3 one future: caption res == eff res
                                    cap_row = ui["scale_rows"][ui["scale_sel"]]
                                    if "@" in cap_row:
                                        got = cap_row.split("@")[1].strip()
                                        want = "%dx%d" % ui["eff_res"]
                                        if got != want:
                                            bad["I3"] += 1
                                    # I4 the commit is boot-coherent
                                    w = commit(st)
                                    cf = w.get("ScaleFactor")
                                    if cf is not None:
                                        cw = w.get("WindowWidth",
                                                   ui["eff_res"][0])
                                        ch = w.get("WindowHeight",
                                                   ui["eff_res"][1])
                                        if not fits(cf, cw, ch):
                                            bad["I4"] += 1
                                    # I5 pure: same state, same answer
                                    if derive(st) != ui:
                                        bad["I5"] += 1
                                    # I6 res rows never exceed the mode's cap
                                    if ui["res_rows"] is not None:
                                        capm = st.cap \
                                            if ui["eff_mode"] == MODE_F \
                                            else st.desk
                                        for r in ui["res_rows"]:
                                            rw, rh = r.split(" ")[0].split("x")
                                            if (int(rw) > capm[0]
                                                    or int(rh) > capm[1]):
                                                bad["I6"] += 1

    for key, label in (
            ("I1", "selections always exist in their lists"),
            ("I2", "the selected scale always fits the effective res"),
            ("I3", "one future: the scale caption's res IS the res combo's"),
            ("I4", "every commit is coherent (would boot-validate clean)"),
            ("I5", "derive is pure - same state, same answer"),
            ("I6", "no res row exceeds its mode's cap")):
        check("%s %s" % (key, label), bad[key] == 0,
              "%d violation(s)" % bad[key])

    print()
    if FAILURES:
        print("FAIL: %d problem(s):" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("ALL PASS (%d checks: transition rows + swept invariants)" % CHECKS[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
