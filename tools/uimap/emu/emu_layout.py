"""
emu_layout.py - STAGE 3 of the offline SC4 UI model: the LAYOUT EMULATOR.

Runs SimCity 4's OWN layout machine code under Unicorn, with the window /
font / service APIs stubbed, and records every window create, SetArea,
GZWinMoveTo and ChildAdd. Output = a predicted window tree + rects for a
given scale factor `f` and a font-metric callback -- with no game launch,
no debugger, and no modification of any game file.

WHY THIS EXISTS (METHOD.md section 6, stage 3): so that "what rect will this
label get?" is answered by reading the binary instead of by shipping a build
and looking at it. Companion to tools\\flyout-sim\\emu_hittest.py (which does
the same trick for the CLICK path).

--------------------------------------------------------------------------
WHAT IS REAL AND WHAT IS MODELLED  (be honest about this line)
--------------------------------------------------------------------------
REAL machine code, executed:
  sub_779660    0x00779660  the label factory (parent,id,x,y,pText,align,
                            styleId,R,G,B) - the whole thing, all 3 align
                            branches
  cGZWin::SetArea      0x0099C837   stores L,T,R,B at [this+0xA8..0xB4]
  cGZWin::GZWinMoveTo  0x0099C8C5   SetArea(x,y,x+W,y+H)
  cGZWin::GetW / GetH  0x0099C81B / 0x0099C82A     (R-L / B-T)
  cGZWin::GetArea*     0x0099BCE1   returns &this->L
  cGZWin::SetW/SetSize 0x0099BC68 / 0x0099BCB6

MODELLED (python stubs, because they need the live font/resource system):
  <winTextFactory>->[vt+0x34](id, pText)   create text window
  <winTextFactory>->[vt+0x14](styleId)     font for a style GUID
  <gfx>->[vt+0x88](R,G,B)                  pack a colour
  cIGZWinText::FitWindowToText(b1,b2)      <-- THE ONLY font-dependent step.
        modelled as: area := (L, T, L + measure_w, T + measure_h)
        where (measure_w, measure_h) come from the --measure callback.
  cIGZWinText::SetFont / SetTextColor / SetAlignment / Release
  cIGZWin::SetID / SetFlag / ChildAdd / InvalidateSelf / ...  (no-ops)

The two singleton getters sub_913C72 (win-text factory) and sub_913C1A
(graphics system) are intercepted at their entry address and made to return
our fake service objects. Nothing is written back to the exe on disk - the
image lives only in the emulator's memory.

--------------------------------------------------------------------------
USAGE
--------------------------------------------------------------------------
  python emu_layout.py --selftest
        run the built-in acceptance suite (the ordinance popup, stock and
        2x, patched and unpatched) and print PASS/FAIL per case.

  python emu_layout.py --builder=0x78B980 --len=0x140
        scan that VA range for `call sub_779660` sites, decode the ten
        pushed arguments from the immediates, and emulate each one.
        Use --parent=WxH to say how big the parent window is (needed by
        align 0x63 = fill, which reads parent GetW/GetH).

  python emu_layout.py --label parent=840x125 x=30 y=50 align=0x63 text=99
        emulate one label directly.

  --f=2            scale factor applied to the call-site constants
                   (x,y are multiplied; use it to model a CodePatches table)
  --measure=W,H    force the FitWindowToText result (bypass the callback)
  --resume         skip cases already recorded in state.json
  --fresh          start a new state.json (safe either way)

Every completed work unit is flushed to state.json immediately, so an
interrupted run resumes with --resume. Disassembly of a builder range is
cached under cache\\ so a restart does not redo it.

Both state.json and the cache\\ files are stamped with sha256(exe)[:16] and
the exe byte size (audit 2026-08-02). If the exe on disk no longer matches,
--resume REFUSES to run (exit 2) and a cache entry is recomputed instead of
reused - a cached decode is a claim about bytes at a VA, and a patched exe
moves those bytes without changing anything else the tool can see.
"""

import hashlib
import json
import os
import re
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
STATE = os.path.join(HERE, "state.json")

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000


# ---- exe fingerprint (audit 2026-08-02) -------------------------------------
# Every cached call-site decode and every recorded acceptance case describes
# BYTES AT A VA in one particular build. Nothing recorded which build, so a
# patched/updated exe would let --resume and the cache report success while
# modelling addresses that had moved. Same stamp as common.exe_fingerprint();
# duplicated here for the same reason EXE is duplicated - this module is run
# from emu\ and does not import common.
_fp = None


def exe_fingerprint():
    """(sha256(exe)[:16], byteSize). 64 bits is far past collision risk for
    'is this the same build?'; size is free and catches a truncated read.

    The LAA bit (0x0020 in the PE COFF Characteristics) is MASKED OUT before
    hashing - the 4GB patch flips it and it cannot change an instruction. See
    the long note on tools\\uimap\\common.py:exe_fingerprint; this is the same
    function and the two MUST agree or the pins diverge."""
    global _fp
    if _fp is None:
        with open(EXE, "rb") as fh:
            d = bytearray(fh.read())
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        cofs = pe + 4 + 18
        ch = struct.unpack_from("<H", d, cofs)[0]
        struct.pack_into("<H", d, cofs, ch & ~0x0020)
        _fp = (hashlib.sha256(bytes(d)).hexdigest()[:16], len(d))
    return _fp


# ---- the real functions we execute -----------------------------------------
LABEL_FACTORY = 0x00779660   # sub_779660  label factory (the Stage-3 target)
WIN_SETAREA   = 0x0099C837   # cGZWin::SetArea(l,t,r,b)      [this+0xA8..0xB4]
WIN_MOVETO    = 0x0099C8C5   # cGZWin::GZWinMoveTo(x,y)
WIN_GETW      = 0x0099C81B
WIN_GETH      = 0x0099C82A
WIN_GETAREAP  = 0x0099BCE1   # int32_t* GetArea()  -> &this->L
WIN_SETW      = 0x0099BC68
WIN_SETSIZE   = 0x0099BCB6
SVC_WINTEXT   = 0x00913C72   # lazily-built singleton: the win-text factory
SVC_GFX       = 0x00913C1A   # lazily-built singleton: the graphics system

# ---- fake address space -----------------------------------------------------
HEAP   = 0x10000000          # objects, 0x400 apart
HEAPSZ = 0x00100000
STUBS  = 0x30000000          # one 8-byte landing pad per (vtable, slot)
STUBSZ = 0x00040000
STACK  = 0x20000000
STACKSZ = 0x00100000
SENTINEL = 0xDEADBEEF

# window object field offsets (the game's own layout - see 0x0099C81B)
O_VT   = 0x00
O_AREA = 0xA8                # L,T,R,B
O_CA   = 0xCA                # flag byte tested by SetArea (bit0 = private buf)

# ---- the TEXT LINE-BREAKER, decoded 2026-07-30 (see POPUP-VERDICT.md §5) ----
# Field map of the concrete text class (code region 0x009BC000-0x009C1000):
#   [this+0x128]  WinText FLAGS  <- what cIGZWinText::SetWinTextFlag(long,bool)
#                                   writes. ctor default 0 (0x009C026C).
#                   bit 0x0002 = WORD WRAP
#                   bit 0x0200 = force single line (no breaks at all)
#   [this+0x158]  gutter, ctor default 5            (0x009BFFCC)
#   [this+0x160]  the WRAP WIDTH, recomputed by sub_9BCBC5
#   [this+0x1D4]  optional scrollbar whose width is subtracted
WRAPW_FN      = 0x009BCBC5   # wrapWidth = GetW() - 2*gutter - scrollbarW  (0 if <0)
BREAKER_FN    = 0x009BF3E0   # the line-break pass
BREAK_SWITCH  = 0x009BF486   # the three-way regime test
WRAP_CALL     = 0x009BF4B3   # cIGZFont::CalculateWordsToFitInWidth(buf,len,w,0,2)
NEWLINE_ONLY  = 0x009BF4BB   # the '\n'-only scanner
RELAYOUT_FN   = 0x009BF98B   # re-break every line
TEXT_SETAREA  = 0x009BFCA5   # SetArea override: base SetArea -> WRAPW_FN ->
                             # [+0x160] -> RELAYOUT_FN.  Text RE-WRAPS on resize.
TEXT_GUTTER_DEFAULT = 5
WINTEXT_FLAG_WORDWRAP   = 0x0002
WINTEXT_FLAG_SINGLELINE = 0x0200


def wrap_width_model(win_w, gutter=TEXT_GUTTER_DEFAULT, scrollbar_w=0):
    """sub_9BCBC5, transcribed. Returns the value stored in [this+0x160]."""
    need = 2 * gutter + scrollbar_w
    return (win_w - need) if win_w >= need else 0


def line_break_regime(win_w, flags=0, gutter=TEXT_GUTTER_DEFAULT,
                      scrollbar_w=0):
    """The three-way switch at 0x009BF486, transcribed.
    -> (wrap_width, regime, where)"""
    w = wrap_width_model(win_w, gutter, scrollbar_w)
    if w == 0 or (flags & WINTEXT_FLAG_SINGLELINE):
        return w, "ONE LINE - no breaks at all, not even \\n", "0x%08X" % 0x009BF4D7
    if flags & WINTEXT_FLAG_WORDWRAP:
        return w, "WORD WRAP at %d px" % w, "0x%08X" % WRAP_CALL
    return w, "BREAK ON '\\n' ONLY - then clip horizontally", "0x%08X" % NEWLINE_ONLY


ALIGN_LEFT = 0x00
ALIGN_RIGHT = 0x06
ALIGN_FILL = 0x63
ALIGN_NAMES = {0x00: "left@x", 0x06: "right-edge@x", 0x63: "fill(parent)"}

# vtable slots we implement as python stubs: slot offset -> (name, argcount)
WIN_STUBS = {
    0x038: ("ChildAdd", 1),
    0x100: ("SetID", 1),
    0x110: ("SetFlag", 2),
    0x168: ("InvalidateSelf", 0),
    0x188: ("GetAreaToDrawTo", 0),
    0x190: ("PrivateBuffer", 1),
}
TXT_STUBS = {
    0x008: ("Release", 0),
    0x00C: ("AsIGZWin", 0),
    0x014: ("FitWindowToText", 2),
    0x028: ("SetTextColor", 1),
    0x048: ("SetFont", 1),
    0x054: ("SetAlignment", 1),
}
FAC_STUBS = {
    0x014: ("GetFontForStyle", 1),
    0x034: ("CreateTextWindow", 2),
}
GFX_STUBS = {
    0x088: ("MakeColor", 3),
}


# =============================================================================
#  font metrics
# =============================================================================
class FontModel(object):
    """Parameterised text measurement. This is the ONLY font-dependent input
    to the layout, so it is a callback, not a constant. Calibrate it against a
    live POPKID/MWKID dump before trusting a font-dependent prediction."""

    def __init__(self, scale=1.0, char_w=None, line_h=None, forced=None):
        self.scale = float(scale)
        # 1x defaults are deliberately coarse. They are NOT measured; the only
        # thing calibrated below is line height, from the 2x popup dump
        # (25 px per line at f=2  =>  12.5 px at f=1).
        self.char_w = 6.4 if char_w is None else float(char_w)
        self.line_h = 12.5 if line_h is None else float(line_h)
        self.forced = forced        # (w,h) - overrides everything

    def measure(self, text, style_id):
        """-> (width, height) of the text as the game would autosize it.
        `text` may be a real string OR an int = 'a string this many chars
        long' (call sites give us a resource id, not a string)."""
        if self.forced:
            return int(self.forced[0]), int(self.forced[1])
        if isinstance(text, int):
            n_chars, n_lines = text, 1
        else:
            lines = str(text).split("\n")
            n_chars = max(len(l) for l in lines)
            n_lines = len(lines)
        w = int(round(n_chars * self.char_w * self.scale))
        h = int(round(n_lines * self.line_h * self.scale))
        return w, h

    def describe(self):
        if self.forced:
            return "FORCED %dx%d" % self.forced
        return "char_w=%.2f line_h=%.2f scale=%.2f" % (
            self.char_w, self.line_h, self.scale)


# =============================================================================
#  the emulator
# =============================================================================
class LayoutEmu(object):
    def __init__(self, font, verbose=False):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        self.font = font
        self.verbose = verbose
        self.events = []            # recorded API calls, in order
        self.objects = {}           # addr -> dict(kind=..., ...)
        self._next = HEAP + 0x1000
        self._text_payload = {}     # text-object addr -> (text, style)

        data = open(EXE, "rb").read()
        uc = Uc(UC_ARCH_X86, UC_MODE_32)
        span = max((len(data) + 0xFFF) & ~0xFFF, 0x800000)
        uc.mem_map(IMAGE_BASE, span)
        uc.mem_write(IMAGE_BASE, data)
        uc.mem_map(HEAP, HEAPSZ)
        uc.mem_map(STUBS, STUBSZ)
        uc.mem_map(STACK, STACKSZ)
        self.uc = uc

        # vtables live in the fake heap too
        self.vt_win = self._alloc(0x400)
        self.vt_txt = self._alloc(0x400)
        self.vt_fac = self._alloc(0x400)
        self.vt_gfx = self._alloc(0x400)
        self._fill_vtables()

        # service singletons
        self.obj_fac = self._new_object("winTextFactory", self.vt_fac)
        self.obj_gfx = self._new_object("graphicSystem", self.vt_gfx)

        uc.hook_add(UC_HOOK_CODE, self._hook_stub, begin=STUBS,
                    end=STUBS + STUBSZ)
        uc.hook_add(UC_HOOK_CODE, self._hook_service, begin=SVC_WINTEXT,
                    end=SVC_WINTEXT)
        uc.hook_add(UC_HOOK_CODE, self._hook_service, begin=SVC_GFX,
                    end=SVC_GFX)
        uc.hook_add(UC_HOOK_CODE, self._hook_setarea, begin=WIN_SETAREA,
                    end=WIN_SETAREA)
        uc.hook_add(UC_HOOK_CODE, self._hook_moveto, begin=WIN_MOVETO,
                    end=WIN_MOVETO)

    # -- memory helpers -------------------------------------------------------
    def _alloc(self, size=0x400):
        a = self._next
        self._next += (size + 0xF) & ~0xF
        return a

    def _rd(self, addr, n=4):
        return struct.unpack("<I", self.uc.mem_read(addr, 4))[0] if n == 4 \
            else self.uc.mem_read(addr, n)

    def _rdi(self, addr):
        return struct.unpack("<i", self.uc.mem_read(addr, 4))[0]

    def _wr(self, addr, val):
        self.uc.mem_write(addr, struct.pack("<I", val & 0xFFFFFFFF))

    def _stub_addr(self, vt, slot):
        return STUBS + ((vt - HEAP) & 0xFFFF) * 4 + slot * 2

    def _fill_vtables(self):
        for vt in (self.vt_win, self.vt_txt, self.vt_fac, self.vt_gfx):
            for slot in range(0, 0x400, 4):
                self._wr(vt + slot, self._stub_addr(vt, slot))
        # the geometry slots run the game's REAL code
        for slot, fn in ((0x0A4, WIN_GETW), (0x0A8, WIN_GETH),
                         (0x0C0, WIN_GETAREAP), (0x0CC, WIN_SETW),
                         (0x0D4, WIN_SETSIZE), (0x0DC, WIN_SETAREA),
                         (0x0E0, WIN_MOVETO)):
            self._wr(self.vt_win + slot, fn)

    def _new_object(self, kind, vt, rect=(0, 0, 0, 0), name=None):
        a = self._alloc(0x400)
        self._wr(a + O_VT, vt)
        self.uc.mem_write(a + O_AREA, struct.pack("<4i", *rect))
        self.uc.mem_write(a + O_CA, b"\x00")
        self.objects[a] = {"kind": kind, "name": name or kind, "children": []}
        return a

    def rect_of(self, obj):
        L, T, R, B = struct.unpack("<4i", self.uc.mem_read(obj + O_AREA, 16))
        return (L, T, R, B)

    def geom_of(self, obj):
        L, T, R, B = self.rect_of(obj)
        return {"l": L, "t": T, "r": R, "b": B, "w": R - L, "h": B - T}

    # -- hooks ----------------------------------------------------------------
    def _ret(self, eax, argc):
        from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ESP,
                                       UC_X86_REG_EIP)
        uc = self.uc
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = self._rd(esp)
        uc.reg_write(UC_X86_REG_EAX, eax & 0xFFFFFFFF)
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + argc * 4)
        uc.reg_write(UC_X86_REG_EIP, ret)

    def _args(self, n):
        from unicorn.x86_const import UC_X86_REG_ESP
        esp = self.uc.reg_read(UC_X86_REG_ESP)
        return [struct.unpack("<i", self.uc.mem_read(esp + 4 + 4 * i, 4))[0]
                for i in range(n)]

    def _hook_service(self, uc, addr, size, user):
        obj = self.obj_fac if addr == SVC_WINTEXT else self.obj_gfx
        self.events.append({"api": "GetService",
                            "which": "winTextFactory" if addr == SVC_WINTEXT
                            else "graphicSystem"})
        self._ret(obj, 0)          # cdecl, no args

    def _hook_setarea(self, uc, addr, size, user):
        from unicorn.x86_const import UC_X86_REG_ECX
        this = uc.reg_read(UC_X86_REG_ECX)
        l, t, r, b = self._args(4)
        # The text class's SetArea override (0x009BFCA5) recomputes the wrap
        # width from the NEW rect and re-breaks every line, so record what the
        # engine would compute at this instant.
        ww = wrap_width_model(r - l)
        self.events.append({"api": "SetArea", "this": self._name(this),
                            "l": l, "t": t, "r": r, "b": b,
                            "w": r - l, "h": b - t, "wrap_width_after": ww})
        if self.verbose:
            print("      SetArea(%s, %d,%d,%d,%d) -> %dx%d   "
                  "[wrap width becomes %d]"
                  % (self._name(this), l, t, r, b, r - l, b - t, ww))

    def _hook_moveto(self, uc, addr, size, user):
        from unicorn.x86_const import UC_X86_REG_ECX
        this = uc.reg_read(UC_X86_REG_ECX)
        x, y = self._args(2)
        self.events.append({"api": "GZWinMoveTo", "this": self._name(this),
                            "x": x, "y": y})
        if self.verbose:
            print("      GZWinMoveTo(%s, %d,%d)" % (self._name(this), x, y))

    def _name(self, obj):
        o = self.objects.get(obj)
        return o["name"] if o else "0x%08X" % obj

    def _hook_stub(self, uc, addr, size, user):
        from unicorn.x86_const import UC_X86_REG_ECX
        rel = addr - STUBS
        vt = HEAP + (rel // 4) - ((rel // 4) % 0x400) if False else None
        # decode (vtable, slot) from the landing-pad address
        vt_key = (rel // 4) & ~0x3FF
        slot = ((rel - vt_key * 4) // 2)
        vt = HEAP + vt_key
        this = uc.reg_read(UC_X86_REG_ECX)
        table, tag = ((WIN_STUBS, "win") if vt == self.vt_win else
                      (TXT_STUBS, "txt") if vt == self.vt_txt else
                      (FAC_STUBS, "fac") if vt == self.vt_fac else
                      (GFX_STUBS, "gfx"))
        ent = table.get(slot)
        if ent is None:
            self.events.append({"api": "UNMODELLED",
                                "vtable": tag, "slot": "0x%03X" % slot})
            if self.verbose:
                print("      !! unmodelled %s vtable slot +0x%03X" % (tag, slot))
            self._ret(1, 0)
            return
        name, argc = ent
        args = self._args(argc)
        eax = 1
        if tag == "fac" and name == "CreateTextWindow":
            wid, ptext = args
            win = self._new_object("window", self.vt_win,
                                   name="win:0x%08X" % (wid & 0xFFFFFFFF))
            txt = self._new_object("text", self.vt_txt,
                                   name="text:0x%08X" % (wid & 0xFFFFFFFF))
            self.objects[txt]["win"] = win
            self.objects[win]["id"] = wid & 0xFFFFFFFF
            self._text_payload[txt] = self._pending_text
            eax = txt
            self.events.append({"api": "CreateTextWindow",
                                "id": "0x%08X" % (wid & 0xFFFFFFFF),
                                "win": self.objects[win]["name"]})
        elif tag == "fac" and name == "GetFontForStyle":
            eax = 0x0F000000 | (args[0] & 0xFFFF)
            self.events.append({"api": "GetFontForStyle",
                                "style": "0x%08X" % (args[0] & 0xFFFFFFFF)})
        elif tag == "gfx" and name == "MakeColor":
            r, g, b = args
            eax = (r << 16) | (g << 8) | b
        elif tag == "txt" and name == "AsIGZWin":
            eax = self.objects[this]["win"]
        elif tag == "txt" and name == "FitWindowToText":
            eax = self._fit_window_to_text(this, args)
        elif tag == "txt" and name == "SetAlignment":
            self.events.append({"api": "SetAlignment", "value": args[0]})
        elif tag == "win" and name == "ChildAdd":
            child = args[0]
            self.objects[this]["children"].append(child)
            self.events.append({"api": "ChildAdd", "parent": self._name(this),
                                "child": self._name(child)})
        elif tag == "win" and name == "SetID":
            self.events.append({"api": "SetID",
                                "id": "0x%08X" % (args[0] & 0xFFFFFFFF)})
        self._ret(eax, argc)

    def _fit_window_to_text(self, txt_obj, args):
        """MODELLED cIGZWinText::FitWindowToText(b1, b2).

        The real implementation asks the font system for the caption's
        extent and resizes the window to it. We do the same with the
        --measure callback. Everything downstream of this point is the
        game's own arithmetic."""
        win = self.objects[txt_obj]["win"]
        text, style = self._text_payload.get(txt_obj, (0, 0))
        w, h = self.font.measure(text, style)
        L, T, R, B = self.rect_of(win)
        self.uc.mem_write(win + O_AREA, struct.pack("<4i", L, T, L + w, T + h))
        self.events.append({"api": "FitWindowToText", "modelled": True,
                            "args": args, "text_w": w, "text_h": h})
        if self.verbose:
            print("      FitWindowToText%s -> MODELLED text extent %dx%d"
                  % (tuple(args), w, h))
        return 1

    # -- the drive ------------------------------------------------------------
    def run_label(self, parent_rect, id_, x, y, text, align, style,
                  rgb=(0x44, 0x55, 0x66)):
        """Execute the REAL sub_779660 and return the resulting geometry."""
        from unicorn import UcError
        from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_ECX,
                                       UC_X86_REG_EBX, UC_X86_REG_EBP,
                                       UC_X86_REG_ESI, UC_X86_REG_EDI,
                                       UC_X86_REG_EIP, UC_X86_REG_EAX)
        uc = self.uc
        self.events = []
        parent = self._new_object("window", self.vt_win, rect=parent_rect,
                                  name="parent")
        self._pending_text = (text, style)
        # sub_779660 is a __thiscall on the dialog controller; nothing in the
        # code path we execute touches `this`, so any valid pointer will do.
        controller = self._new_object("controller", self.vt_win, name="ctrl")

        args = [parent, id_, x, y, 0xAAAA0000, align, style,
                rgb[0], rgb[1], rgb[2]]
        sp = STACK + STACKSZ - 0x1000
        for a in reversed(args):
            sp -= 4
            uc.mem_write(sp, struct.pack("<I", a & 0xFFFFFFFF))
        sp -= 4
        uc.mem_write(sp, struct.pack("<I", SENTINEL))
        uc.reg_write(UC_X86_REG_ESP, sp)
        uc.reg_write(UC_X86_REG_ECX, controller)
        for r in (UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_ESI,
                  UC_X86_REG_EDI):
            uc.reg_write(r, 0)
        err = None
        try:
            uc.emu_start(LABEL_FACTORY, SENTINEL, count=2000000)
        except UcError as e:
            err = "emu fault @0x%08X: %s" % (uc.reg_read(UC_X86_REG_EIP), e)

        label_win = None
        for a, o in self.objects.items():
            if o["kind"] == "window" and o.get("id") == (id_ & 0xFFFFFFFF):
                label_win = a
        out = {
            "error": err,
            "parent": self.geom_of(parent),
            "label": self.geom_of(label_win) if label_win else None,
            # sub_779660 returns GetW() taken right after FitWindowToText,
            # i.e. the autosized TEXT width (0x007796E6 -> [esp+0x28]).
            "returned_text_width": (uc.reg_read(UC_X86_REG_EAX)
                                    if err is None else None),
            "events": list(self.events),
            "attached": any(e.get("api") == "ChildAdd" for e in self.events),
        }
        return out


# =============================================================================
#  call-site extraction (Stage-2 style constant decode, cached)
# =============================================================================
def scan_callsites(builder_va, length, target=LABEL_FACTORY):
    """Find `call target` inside [builder_va, builder_va+length) and recover
    the ten arguments from the preceding `push imm` instructions.

    Args that are not immediates (the parent window, the text pointer) come
    back as the string 'dyn'. Cached to cache\\callsites-*.json.

    The cache is keyed by (builder, length, target) only - NOT by exe - so it
    is stamped with the exe fingerprint and a mismatch recomputes instead of
    handing back immediates decoded from a build that no longer exists. Files
    written before 2026-08-02 are a bare JSON list with no stamp; those are
    treated as stale (recomputed), never rejected with an exception."""
    key = "callsites-%08X-%X-%08X.json" % (builder_va, length, target)
    path = os.path.join(CACHE, key)
    sha, size = exe_fingerprint()
    if os.path.exists(path):
        cached = None
        try:
            with open(path, "r") as fh:
                cached = json.load(fh)
        except Exception:
            cached = None
        if (isinstance(cached, dict)
                and cached.get("exeSha256_16") == sha
                and cached.get("exeSize") == size):
            return cached["sites"]
        why = ("legacy unstamped cache" if isinstance(cached, list)
               else "exe fingerprint changed")
        print("[cache] recomputing %s (%s)" % (key, why))

    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    data = open(EXE, "rb").read()
    off = builder_va - IMAGE_BASE
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    insns = list(md.disasm(data[off:off + length], builder_va))

    sites = []
    for i, ins in enumerate(insns):
        if ins.mnemonic != "call":
            continue
        try:
            if int(ins.op_str, 0) != target:
                continue
        except ValueError:
            continue
        # walk backwards collecting pushes until we have 10 slots' worth.
        pushes = []           # (va, value_or_'dyn')
        j = i - 1
        consumed = 0          # stack slots eaten by intervening calls
        while j >= 0 and len(pushes) < 10:
            p = insns[j]
            if p.mnemonic == "push":
                v = None
                if re.fullmatch(r"0x[0-9a-f]+|\d+", p.op_str):
                    v = int(p.op_str, 0)
                if consumed > 0:
                    consumed -= 1          # this push fed an inner call
                else:
                    pushes.append((p.address, v if v is not None else "dyn"))
            elif p.mnemonic == "call":
                # a nested call eats some of the pushes above it; we cannot
                # know how many without following it, so assume a thiscall
                # with no stack args unless it is a known 'ret N'.
                consumed += _callee_argc(data, p)
            j -= 1
        # NOTE: args are pushed right-to-left, so walking BACKWARDS from the
        # call finds arg1 first. Do NOT reverse this list.
        names = ["parent", "id", "x", "y", "pText", "align", "styleId",
                 "R", "G", "B"]
        got = {}
        for k, nm in enumerate(names):
            if k < len(pushes):
                got[nm] = pushes[k][1]
                got[nm + "_va"] = "0x%08X" % pushes[k][0]
            else:
                got[nm] = "dyn"
        got["call_va"] = "0x%08X" % ins.address
        sites.append(got)

    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"version": 2, "exeSha256_16": sha, "exeSize": size,
                   "builder": "0x%08X" % builder_va, "len": length,
                   "target": "0x%08X" % target, "sites": sites}, fh, indent=1)
    return sites


def _callee_argc(data, ins):
    """How many stack slots does this call consume? Read the callee's `ret N`
    if it is a direct call; 0 otherwise (indirect thiscall getters)."""
    try:
        tgt = int(ins.op_str, 0)
    except ValueError:
        return 0
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    off = tgt - IMAGE_BASE
    if off < 0 or off + 0x400 > len(data):
        return 0
    for k in md.disasm(data[off:off + 0x400], tgt):
        if k.mnemonic in ("ret", "retn"):
            return (int(k.op_str, 0) // 4) if k.op_str else 0
    return 0


def read_imm8(va):
    """Read the imm8 that lives at `va` in the SHIPPED exe (never modified).
    Used to quote a builder constant in its stock encoding."""
    with open(EXE, "rb") as fh:
        fh.seek(va - IMAGE_BASE)
        return struct.unpack("<b", fh.read(1))[0]


# =============================================================================
#  state / resume
# =============================================================================
def _blank_state():
    sha, size = exe_fingerprint()
    return {"version": 2, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "exe": EXE, "exeSha256_16": sha, "exeSize": size,
            "cases": {}, "notes": []}


def load_state(fresh=False, resume=False):
    """Load state.json, refusing to reuse one built from a different exe.

    A recorded case is a claim about what the game's own machine code did at
    a VA; if the exe underneath changed, every 'done' flag in the file is a
    claim about bytes that may no longer be there. Unstamped files (written
    before 2026-08-02) are treated as stale, not as an error.
    """
    if fresh or not os.path.exists(STATE):
        return _blank_state()
    try:
        with open(STATE, "r") as fh:
            st = json.load(fh)
    except Exception:
        return _blank_state()

    sha, size = exe_fingerprint()
    got = (st.get("exeSha256_16"), st.get("exeSize"))
    if got == (sha, size):
        return st

    why = ("no exe fingerprint (written before the stamp existed)"
           if got[0] is None else
           "built from a DIFFERENT exe: state says %s/%s bytes, the exe on "
           "disk is %s/%d bytes" % (got[0], got[1], sha, size))
    if resume:
        sys.stderr.write(
            "\n*** STALE state.json - REFUSING TO --resume ***\n"
            "  %s\n  %s\n"
            "  Re-run WITHOUT --resume (add --fresh to overwrite the file).\n\n"
            % (STATE, why))
        sys.exit(2)
    print("[state] ignoring stale state.json (%s); starting fresh" % why)
    return _blank_state()


def save_state(st):
    st["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    # Re-stamp on every write so the file always names the exe it describes,
    # including states that were created before this field existed.
    sha, size = exe_fingerprint()
    st["exe"], st["exeSha256_16"], st["exeSize"] = EXE, sha, size
    tmp = STATE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(st, fh, indent=1)
    os.replace(tmp, STATE)


# =============================================================================
#  the acceptance suite - the ordinance description popup
# =============================================================================
# Builder facts, all read from the exe (VAs quoted in POPUP-VERDICT.md):
#   0x0078B99F  push 0x7d          popup height        = 125   (NEVER scaled)
#   0x0078B9A1  sub ebx,0x3c       popup width         = dialogW - 60
#   0x0078B9D7  push 0x1e          popup x             = 30
#   0x0078BA35  sub_779660(... id 0x0ABCE000, x=10, y=5,  align 0    )  TITLE
#   0x0078BA81  sub_779660(... id 0x0ABCE001, x=15, y=25, align 0x63 )  BODY
POPUP = {
    "height_va": 0x0078B9A0,     # imm8 of `push 0x7d`
    "margin_va": 0x0078B9A3,     # imm8 of `sub ebx,0x3c`
    "x_va": 0x0078B9D8,          # imm8 of `push 0x1e`
    "dialog_w_1x": 450,          # ordinance band-art family 0x140155F0-F7
}

ACCEPT = [
    # name, dialog width, popup margin, popup height, body x, body y,
    #       expected (w,h), where the measurement came from
    ("BODY  2x, x/y UNPATCHED (15,25)  - City Lottery dump",
     900, 60, 125, 15, 25, (795, 75),
     "BUDGET-DETAIL-ANATOMY.md section POPUP P2 - 'came out 795x75'"),
    ("BODY  2x, x/y PATCHED   (30,50)  - Smoke Detector dump",
     900, 60, 125, 30, 50, (750, 25),
     "BUDGET-DETAIL-ANATOMY.md section POPUP P1 - body (30,50) 750x25"),
    ("BODY  1x stock          (15,25)  - PREDICTION, never captured",
     450, 60, 125, 15, 25, (345, 75),
     "no live capture exists at f=1 (section POPUP P4 question 1)"),
    ("BODY  2x with the height+margin+x fix (this file's recommendation)",
     900, 120, 250, 30, 50, (690, 150),
     "PREDICTION - exactly 2x the 1x stock row above"),
]


def run_acceptance(resume=False, fresh=False, verbose=False):
    st = load_state(fresh=fresh, resume=resume)
    print("=" * 78)
    print("SC4 LAYOUT EMULATOR - acceptance suite (ordinance description popup)")
    print("=" * 78)
    print("real code executed : sub_779660 @0x%08X, cGZWin::SetArea @0x%08X,"
          % (LABEL_FACTORY, WIN_SETAREA))
    print("                     GZWinMoveTo @0x%08X, GetW/GetH/GetArea"
          % WIN_MOVETO)
    print("modelled           : FitWindowToText (font extent) + service stubs")
    print("exe on disk        : untouched; image is mapped read-only into the")
    print("                     emulator and patched only in emulator memory")
    print()
    print("stock encodings read back from the shipped exe:")
    print("   0x%08X  popup height imm8      = %d" %
          (POPUP["height_va"], read_imm8(POPUP["height_va"])))
    print("   0x%08X  popup width margin imm8= %d" %
          (POPUP["margin_va"], read_imm8(POPUP["margin_va"])))
    print("   0x%08X  popup x imm8           = %d" %
          (POPUP["x_va"], read_imm8(POPUP["x_va"])))
    print()

    npass = nfail = nskip = 0
    for name, dlg_w, margin, height, bx, by, expect, src in ACCEPT:
        key = "accept::" + name
        if resume and key in st["cases"] and st["cases"][key].get("done"):
            print("[skip] %s  (already in state.json)" % name)
            nskip += 1
            continue
        parent_rect = (0, 0, dlg_w - margin, height)   # the popup CONTENT win
        font = FontModel(scale=1.0, forced=None)
        emu = LayoutEmu(font, verbose=verbose)
        # `text=120` = "a 120-character description". Deliberately long, to
        # show the fill branch does not care what the text is.
        res = emu.run_label(parent_rect, 0x0ABCE001, bx, by, 120,
                            ALIGN_FILL, 0xEA85D308)
        lab = res["label"]
        got = (lab["w"], lab["h"]) if lab else None
        ok = (got == expect)
        npass += ok
        nfail += (not ok)
        print("%s %s" % ("[PASS]" if ok else "[FAIL]", name))
        print("        parent(popup content) = %dx%d  (dialog %d - margin %d,"
              " height %d)" % (parent_rect[2], parent_rect[3], dlg_w, margin,
                               height))
        print("        body x=%d y=%d align=0x63 fill  ->  predicted %s,"
              " measured/expected %s" % (bx, by, got, expect))
        print("        source: %s" % src)
        if res["error"]:
            print("        EMU ERROR: %s" % res["error"])
        st["cases"][key] = {"done": True, "pass": bool(ok), "got": got,
                            "expect": list(expect),
                            "inputs": {"dialog_w": dlg_w, "margin": margin,
                                       "height": height, "x": bx, "y": by},
                            "when": time.strftime("%Y-%m-%d %H:%M:%S")}
        save_state(st)     # flush after EVERY case - resumability

    # font-dependent control: the TITLE (align 0) - width = 1000 - textWidth
    key = "accept::TITLE 2x align-0 width == 1000 - textWidth"
    if resume and st["cases"].get(key, {}).get("done"):
        print("[skip] TITLE 2x align-0  (already in state.json)")
        nskip += 1
    else:
        font = FontModel(scale=1.0, forced=(303, 37))   # back-solved, see below
        emu = LayoutEmu(font, verbose=verbose)
        res = emu.run_label((0, 0, 840, 125), 0x0ABCE000, 20, 10, "title",
                            ALIGN_LEFT, 0xEA85D307)
        lab = res["label"]
        got = (lab["w"], lab["h"]) if lab else None
        ok = got == (697, 37)
        npass += ok
        nfail += (not ok)
        print("%s TITLE 2x align-0: window width must be 1000 - textWidth" %
              ("[PASS]" if ok else "[FAIL]"))
        print("        forced text extent 303x37 (back-solved from the live")
        print("        697x37 dump) -> predicted %s, measured (697, 37)" % (got,))
        print("        this is the ONLY font-dependent case in the popup")
        st["cases"][key] = {"done": True, "pass": bool(ok), "got": got,
                            "expect": [697, 37],
                            "when": time.strftime("%Y-%m-%d %H:%M:%S")}
        save_state(st)

    print()
    report_wrap_regimes(st)
    print()
    print("acceptance: %d pass, %d fail, %d skipped   (state: %s)"
          % (npass, nfail, nskip, STATE))
    return nfail == 0


def report_wrap_regimes(st=None):
    """Answer 'what width does the text wrap against, and when'.

    Transcribed from sub_9BCBC5 (wrap width) and the three-way switch at
    0x009BF486 (regime). The wrap width is NOT a constant anywhere: it is
    recomputed from the window's own width by the text class's SetArea
    override (0x009BFCA5), which then re-breaks every line."""
    print("=" * 78)
    print("WRAP REGIME - where the line breaks come from")
    print("=" * 78)
    print("wrap width = GetW() - 2*gutter(%d) - scrollbarW      [sub_9BCBC5 @0x%08X]"
          % (TEXT_GUTTER_DEFAULT, WRAPW_FN))
    print("recomputed + re-broken on EVERY SetArea               [override @0x%08X]"
          % TEXT_SETAREA)
    print("regime switch @0x%08X:  w==0 or flags&0x200 -> one line;"
          % BREAK_SWITCH)
    print("   flags&0x0002 -> word wrap @0x%08X;  else -> '\\n' only @0x%08X"
          % (WRAP_CALL, NEWLINE_ONLY))
    print("flags live at [this+0x128]; ctor default 0 (0x009C026C); sub_779660")
    print("never calls SetWinTextFlag -> WORD WRAP IS OFF on every label it makes.")
    print()
    print("  body window   flags   wrap width   regime")
    rows = [(750, 0x0000, "shipped 2x today"),
            (750, 0x0002, "shipped 2x + SetWinTextFlag(2,true)"),
            (690, 0x0000, "2x after the geometry fix, flag still off"),
            (690, 0x0002, "2x after the geometry fix + the flag  <-- the cure"),
            (345, 0x0000, "1x stock (prediction)"),
            (345, 0x0002, "1x stock if the flag were on")]
    for w, fl, note in rows:
        ww, regime, where = line_break_regime(w, fl)
        print("  %4d          0x%04X  %6d       %-42s %s"
              % (w, fl, ww, regime, note))
    if st is not None:
        st.setdefault("notes", []).append(
            "wrap width = GetW()-2*5, sub_9BCBC5 @0x009BCBC5; regime switch "
            "@0x009BF486; flags [this+0x128] default 0 => '\\n'-only breaks; "
            "cure = cIGZWinText::SetWinTextFlag(2,true) on 0x0ABCE001")
        save_state(st)


# =============================================================================
#  generic builder mode
# =============================================================================
def run_builder(builder_va, length, parent_wh, f=1.0, resume=False,
                fresh=False, verbose=False, forced=None):
    st = load_state(fresh=fresh, resume=resume)
    sites = scan_callsites(builder_va, length)
    print("=" * 78)
    print("builder 0x%08X (+0x%X)  -> %d call(s) to sub_779660"
          % (builder_va, length, len(sites)))
    print("parent window modelled as %dx%d ; scale f=%.3g"
          % (parent_wh[0], parent_wh[1], f))
    print("=" * 78)
    out = []
    for s in sites:
        key = "builder::%08X::%s" % (builder_va, s["call_va"])
        if resume and st["cases"].get(key, {}).get("done"):
            print("[skip] %s (cached)" % s["call_va"])
            out.append(st["cases"][key]["result"])
            continue
        x = s["x"] if isinstance(s["x"], int) else 0
        y = s["y"] if isinstance(s["y"], int) else 0
        align = s["align"] if isinstance(s["align"], int) else 0
        style = s["styleId"] if isinstance(s["styleId"], int) else 0
        wid = s["id"] if isinstance(s["id"], int) else 0
        xs, ys = int(round(x * f)), int(round(y * f))
        font = FontModel(scale=f, forced=forced)
        emu = LayoutEmu(font, verbose=verbose)
        res = emu.run_label((0, 0, parent_wh[0], parent_wh[1]), wid, xs, ys,
                            60, align, style)
        lab = res["label"]
        rec = {"call_va": s["call_va"], "id": "0x%08X" % (wid & 0xFFFFFFFF),
               "x": xs, "y": ys, "align": "0x%02X" % align,
               "align_name": ALIGN_NAMES.get(align, "?"),
               "style": "0x%08X" % (style & 0xFFFFFFFF),
               "rect": lab, "error": res["error"]}
        print("  %s  id=%s  x=%-5d y=%-5d align=%-4s (%s)"
              % (s["call_va"], rec["id"], xs, ys, rec["align"],
                 rec["align_name"]))
        if lab:
            print("       -> (%d,%d) %dx%d" % (lab["l"], lab["t"],
                                               lab["w"], lab["h"]))
        if res["error"]:
            print("       EMU ERROR: %s" % res["error"])
        out.append(rec)
        st["cases"][key] = {"done": True, "result": rec,
                            "when": time.strftime("%Y-%m-%d %H:%M:%S")}
        save_state(st)
    return out


# =============================================================================
def main():
    argv = sys.argv[1:]
    if not argv or "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    resume = "--resume" in argv
    fresh = "--fresh" in argv
    verbose = "--verbose" in argv or "-v" in argv
    f = 1.0
    parent = (840, 125)
    forced = None
    builder = length = None
    for a in argv:
        if a.startswith("--f="):
            f = float(a.split("=", 1)[1])
        elif a.startswith("--parent="):
            w, h = a.split("=", 1)[1].lower().split("x")
            parent = (int(w, 0), int(h, 0))
        elif a.startswith("--measure="):
            w, h = a.split("=", 1)[1].split(",")
            forced = (int(w, 0), int(h, 0))
        elif a.startswith("--builder="):
            builder = int(a.split("=", 1)[1], 0)
        elif a.startswith("--len="):
            length = int(a.split("=", 1)[1], 0)

    if "--selftest" in argv:
        ok = run_acceptance(resume=resume, fresh=fresh, verbose=verbose)
        return 0 if ok else 1

    if builder is not None:
        run_builder(builder, length or 0x200, parent, f=f, resume=resume,
                    fresh=fresh, verbose=verbose, forced=forced)
        return 0

    if "--label" in argv:
        kv = {}
        for a in argv:
            if "=" in a and not a.startswith("--"):
                k, v = a.split("=", 1)
                kv[k] = v
        pw, ph = (kv.get("parent", "840x125")).lower().split("x")
        text = kv.get("text", "60")
        text = int(text) if text.isdigit() else text
        emu = LayoutEmu(FontModel(scale=f, forced=forced), verbose=True)
        res = emu.run_label((0, 0, int(pw, 0), int(ph, 0)),
                            int(kv.get("id", "0x1"), 0),
                            int(kv.get("x", "0"), 0),
                            int(kv.get("y", "0"), 0), text,
                            int(kv.get("align", "0"), 0),
                            int(kv.get("style", "0"), 0))
        print(json.dumps({k: v for k, v in res.items() if k != "events"},
                         indent=1))
        for e in res["events"]:
            print("   ", e)
        return 0

    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
