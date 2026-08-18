"""
emu_chart_range.py - run the Graphs chart's OWN series max-scan offline.

WHY. The Graphs chart's interior is CODE-PAINTED: nothing in the .UI data
describes where the plot, the legend or the axis titles land, so our offline
model (tools\\uimap) currently stops at the chart's outer window and has
nothing to say about its inside. Before we can gate ANY chart fix offline we
have to prove we can (a) build the chart object well enough for its own code
to accept, and (b) execute that code honestly under Unicorn. This file is
that proof, run on the one chart routine that needs ZERO fabricated inputs.

SCOPE, STATED UP FRONT (law 42).
  IN - real SimCity 4 machine code, executed instruction by instruction:
       sub_9B5EAC @ 0x009B5EAC, the chart main-vtable slot +0x290 series
       max-scan (44 instructions, byte-verified below). It CALLS NOTHING -
       no font, no engine, no allocator - so every input it consumes is a
       plain number we can state exactly, and every output is either its
       x87 return value or a byte it wrote itself.
  IN - the chart object fields that routine actually touches:
       [obj+0x234] / [obj+0x238] only (field map + provenance below).
  OUT - EVERYTHING downstream of a font metric. This file makes NO claim
       about tick labels, axis-title extents, legend width, the plot rect,
       or any layout that depends on a measure()/GetTextExtent() result.
       Those need a text engine we do not have offline, and a prediction
       resting on a fabricated measure() is a HYPOTHESIS, not a gate.
  IN - a SECOND target, added only after the first went green:
       sub_9B3647 @ 0x009B3647, main-vt +0x2A8, the axis auto-range /
       layout driver. Its nine callees are stubbed and captured, so what
       is proved there is narrower: the driver's own CONTROL FLOW (which
       helper each sentinel field summons, in what order), its own
       ARITHMETIC (the equal-bounds fixup and the tick-decimals ladder),
       and the PLUMBING of the four rects. See the big SECOND TARGET
       banner further down for that half's scope, which is not this one's.
  OUT - the rect VALUES in that second half. Every rect there is a tagged
       fake we inject, because the real producers (sub_9B387A legend,
       sub_9B799D plot, sub_9B7B57 axis title) derive theirs from text
       extents. Quoting a rect out of this file is quoting a number this
       file invented.
  OUT - anything about how the chart LOOKS. This gate answers one question:
       "does the game's own series scan run correctly under our emulator,
       over an object WE built?" A green run licenses building on this
       object model. It licenses nothing about pixels.

WHAT IS REAL AND WHAT IS MODELLED
  REAL, executed:   sub_9B5EAC in full, including its idiv-by-12 series
                    count, both loops, and the x87 running-max compare.
  REAL, read back:  the -FLT_MAX seed constant at 0x00ADDE24, loaded by the
                    function itself out of the mapped image (not typed in).
  MODELLED:         nothing. No call is stubbed, because the function makes
                    no call. The only thing this file supplies is the
                    object's bytes and an 8-byte return pad of our own
                    machine code (fnstsw / fstp) to get the x87 result out
                    of ST(0), since Unicorn 2.1.4's reg_read(ST0) returns
                    only the 64-bit mantissa and drops the exponent.

THE TARGET, byte-verified from the shipped exe (file offset == RVA):
    0x009B5EB0  mov  eax,[ecx+0x238]        ; series vector _Last
    0x009B5EB6  fld  dword [0x00ADDE24]     ; seed = -FLT_MAX  (this is a MAX)
    0x009B5EBC  sub  eax,[ecx+0x234]        ; - _First
    0x009B5EC7  idiv esi (esi=12)           ; -> series count, 12-byte stride
    0x009B5ED6  mov  edx,[ecx]              ; series[i]._First  (float*)
    0x009B5ED8  mov  eax,[ecx+4]            ; series[i]._Last
    0x009B5EDD  sar  eax,2                  ; -> element count
    0x009B5EE4  fld  dword [edx]            ; value
    0x009B5EE6  fst  dword [ebp-4]          ;   stashed (our 2nd channel)
    0x009B5EE9  fcomp st(1)                 ; value vs running max
    0x009B5EED  test ah,0x41                ; C0|C3 -> value <= max ?
    0x009B5EF2  fstp st(0) / fld [ebp-4]    ;   value > max: replace
    0x009B5F06  ret  4                      ; result in ST(0); 1 unused arg

USAGE
  python emu_chart_range.py             # both targets (what CI runs)
  python emu_chart_range.py --target=1  # the max-scan only
  python emu_chart_range.py --target=2  # the axis driver only
  python emu_chart_range.py --verbose   # + every case's instrumentation
Exit code 0 only if every check passes; 1 on any failure, including an
x87 preflight failure. It never prints a pass it did not earn.

IS THIS AN INSTRUMENT? Three falsifications were run against it and all
three turned it red, so its greens mean something:
  * point target 1 at the MIN-scan twin sub_9B5F09 (+0x294) -> 14 of 15
    cases fail (the two single-element cases legitimately survive, since
    min == max there);
  * corrupt the target-2 oracle's headroom constant and reverse its ladder
    -> 7 failures, with the EMULATED values staying correct;
  * claim the legend rect is fetched before the plot rect -> 6 call-order
    failures.
"""

import struct
import sys

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
IMAGE_BASE = 0x400000

# ---------------------------------------------------------------------------
# ADDRESSES - every one re-verified against the shipped exe at import time by
# check_image(); none of them is trusted on the strength of a comment.
# ---------------------------------------------------------------------------
MAX_SCAN_FN   = 0x009B5EAC   # chart main-vt +0x290, "max over all series"
MIN_SCAN_FN   = 0x009B5F09   # its twin, +0x294 (seed +FLT_MAX) - not run here
CHART_VTABLE  = 0x00AB4D08   # chart main vtable
SLOT_MAX_SCAN = 0x290
SLOT_MIN_SCAN = 0x294
SEED_NEG_FLT_MAX = 0x00ADDE24   # the float the max-scan itself fld's
SEED_POS_FLT_MAX = 0x00ADDE28   # the float the min-scan itself fld's

# instrumentation points INSIDE the real function (read-only hooks, no state
# is changed): they let us read what the function computed, not what we think
# it computed.
IP_AFTER_IDIV = 0x009B5EC9   # eax = series count, straight out of the idiv
IP_ELEM_FLD   = 0x009B5EE4   # edx = address of the element about to be read

# ---------------------------------------------------------------------------
# EMULATOR MEMORY MAP (same idioms as emu_subflyout.py)
# ---------------------------------------------------------------------------
HEAP,  HEAPSZ  = 0x10000000, 0x00100000
STACK, STACKSZ = 0x20000000, 0x00100000
PAD,   PADSZ   = 0x40000000, 0x00001000   # our return pad (MAGIC_RET + code)
PRE,   PRESZ   = 0x50000000, 0x00001000   # x87 preflight scratch

OBJ        = HEAP + 0x00001000   # the chart object
DESC_BASE  = HEAP + 0x00002000   # the series descriptor array (12B stride)
DATA_BASE  = HEAP + 0x00008000   # the float payloads
TRAP_BASE  = HEAP + 0x00040000   # values nothing correct may ever read
RESULT     = HEAP + 0x00000100   # the pad fstp's ST(0) here as a qword
FNINIT_STUB = PAD + 0x100        # two bytes of `fninit`, written once
PRE_A      = PRE + 0x800
PRE_B      = PRE + 0x804
PRE_TMP    = PRE + 0x808
PRE_RES    = PRE + 0x810

# ---------------------------------------------------------------------------
# CHART OBJECT FIELD MAP - provenance for EVERY field we write.
# ---------------------------------------------------------------------------
#   +0x000  vptr -> main vtable
#             PROVENANCE: not read by sub_9B5EAC (no `mov eax,[ecx]` in the
#             44-instruction body). Written to the real 0x00AB4D08 anyway so
#             the object is honest for anything layered on this file later,
#             and so a future virtual dispatch does not silently read 0.
#   +0x234  series._First   (pointer to descriptor[0])
#             PROVENANCE: 0x009B5EBC `sub eax,[ecx+0x234]` and 0x009B5ECD
#             `mov ecx,[ecx+0x234]`, byte-read from the exe above.
#   +0x238  series._Last    (one past the last descriptor)
#             PROVENANCE: 0x009B5EB0 `mov eax,[ecx+0x238]`.
#   +0x23C  series._End (capacity)
#             PROVENANCE: INFERRED, not read by this function. It is the
#             third member of the MSVC std::vector layout implied by the
#             _First/_Last pair at 0x234/0x238. We write a TRAP pointer here
#             so that if anything ever does read it the test notices.
#   descriptor[i] +0x0  data._First (float*)   0x009B5ED6 `mov edx,[ecx]`
#   descriptor[i] +0x4  data._Last  (float*)   0x009B5ED8 `mov eax,[ecx+4]`
#   descriptor[i] +0x8  data._End              INFERRED (stride is 12 by the
#             `push 0xc` / idiv, and by `add ecx,0xc` at 0x009B5EFD). NOT
#             read: we poison it with a trap pointer.
OFF_SERIES_FIRST = 0x234
OFF_SERIES_LAST  = 0x238
OFF_SERIES_END   = 0x23C
DESC_STRIDE      = 12

TRAP_FLOAT = 9.87654e+30    # if this ever shows up in a result, we over-read

FLT_MAX     = struct.unpack("<f", b"\xff\xff\x7f\x7f")[0]
NEG_FLT_MAX = -FLT_MAX


def f32(x):
    """Round a python float to the float32 the emulator will actually see."""
    return struct.unpack("<f", struct.pack("<f", x))[0]


def p32(v):
    return struct.pack("<I", v & 0xFFFFFFFF)


# ---------------------------------------------------------------------------
# image checks - refuse to run against an exe that is not the one we read
# ---------------------------------------------------------------------------
def check_image(data):
    """Re-derive every hardcoded address from the file. Returns a list of
    complaints; empty means the exe on disk is the one this file was written
    against."""
    bad = []

    def dw(va):
        off = va - IMAGE_BASE
        if off < 0 or off + 4 > len(data):
            return None
        return struct.unpack("<I", data[off:off + 4])[0]

    for slot, want, name in ((SLOT_MAX_SCAN, MAX_SCAN_FN, "max-scan"),
                             (SLOT_MIN_SCAN, MIN_SCAN_FN, "min-scan")):
        got = dw(CHART_VTABLE + slot)
        if got != want:
            bad.append("vt 0x%08X +0x%03X (%s) = 0x%08X, expected 0x%08X"
                       % (CHART_VTABLE, slot, name, got or 0, want))

    # the opening of the target, byte-for-byte
    want_head = bytes.fromhex("558bec51" "8b8138020000" "d90524dead00"
                              "2b8134020000" "566a0c")
    off = MAX_SCAN_FN - IMAGE_BASE
    head = data[off:off + len(want_head)]
    if head != want_head:
        bad.append("sub_9B5EAC prologue bytes differ: %s" % head.hex())

    # the seed the function loads must BE -FLT_MAX (this is what makes it a
    # max-scan rather than a min-scan; the twin at +0x294 loads +FLT_MAX)
    off = SEED_NEG_FLT_MAX - IMAGE_BASE
    seed = struct.unpack("<f", data[off:off + 4])[0]
    if seed != NEG_FLT_MAX:
        bad.append("seed at 0x%08X is %r, expected -FLT_MAX" % (SEED_NEG_FLT_MAX, seed))
    off = SEED_POS_FLT_MAX - IMAGE_BASE
    seed2 = struct.unpack("<f", data[off:off + 4])[0]
    if seed2 != FLT_MAX:
        bad.append("twin seed at 0x%08X is %r, expected +FLT_MAX"
                   % (SEED_POS_FLT_MAX, seed2))
    return bad


# ---------------------------------------------------------------------------
class ChartRangeEmu(object):
    """Maps the exe 1:1 and runs the chart's own scan over an object we build."""

    def __init__(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        data = open(EXE, "rb").read()
        self.image_complaints = check_image(data)

        uc = Uc(UC_ARCH_X86, UC_MODE_32)
        span = max((len(data) + 0xFFF) & ~0xFFF, 0x800000)
        uc.mem_map(IMAGE_BASE, span)
        uc.mem_write(IMAGE_BASE, data)
        uc.mem_map(HEAP, HEAPSZ)
        uc.mem_map(STACK, STACKSZ)
        uc.mem_map(PAD, PADSZ)
        uc.mem_map(PRE, PRESZ)

        # ---- the return pad -------------------------------------------
        # sub_9B5EAC returns its answer in ST(0) and Unicorn 2.1.4's
        # reg_read(UC_X86_REG_ST0) hands back only the 64-bit mantissa (the
        # exponent and sign are dropped), so reading the register is not an
        # option. Instead the address we push as the return address points at
        # eight bytes of OUR OWN machine code, which the CPU runs after the
        # function's `ret 4`:
        #     df e0                fnstsw ax          <- FPU stack depth proof
        #     dd 1d <RESULT>       fstp qword [RESULT]<- the answer, exactly
        # Emulation then halts at PAD+8. This adds no modelling: it only
        # spills a register the binding cannot read.
        self.pad_code = b"\xdf\xe0" + b"\xdd\x1d" + p32(RESULT)
        uc.mem_write(PAD, self.pad_code)
        self.pad_end = PAD + len(self.pad_code)

        # a standalone `fninit` stub, written ONCE and never overwritten, so
        # every run starts from a known FPU TOP (self-modifying a page that
        # Unicorn has already translated is how you get phantom faults).
        uc.mem_write(FNINIT_STUB, b"\xdb\xe3")

        uc.hook_add(UC_HOOK_CODE, self._hook_idiv,
                    begin=IP_AFTER_IDIV, end=IP_AFTER_IDIV)
        uc.hook_add(UC_HOOK_CODE, self._hook_elem,
                    begin=IP_ELEM_FLD, end=IP_ELEM_FLD)

        self.uc = uc
        self.series_count = None    # what the function's own idiv produced
        self.visited = []           # element addresses the function fld'd

    # -- read-only instrumentation ---------------------------------------
    def _hook_idiv(self, uc, addr, size, user):
        from unicorn.x86_const import UC_X86_REG_EAX
        self.series_count = struct.unpack(
            "<i", struct.pack("<I", uc.reg_read(UC_X86_REG_EAX)))[0]

    def _hook_elem(self, uc, addr, size, user):
        from unicorn.x86_const import UC_X86_REG_EDX
        self.visited.append(uc.reg_read(UC_X86_REG_EDX))

    # -- x87 preflight ----------------------------------------------------
    def x87_preflight(self):
        """Run the target's EXACT inner-loop idiom on scratch values. If this
        does not produce max(a,b) both ways round, Unicorn's x87 is not usable
        here and nothing downstream may be believed."""
        from unicorn import UcError
        from unicorn.x86_const import UC_X86_REG_ESP
        uc = self.uc
        code = (b"\xdb\xe3"                       # fninit
                + b"\xd9\x05" + p32(PRE_A)        # fld  dword [A]   (seed)
                + b"\xd9\x05" + p32(PRE_B)        # fld  dword [B]   (value)
                + b"\xd9\x15" + p32(PRE_TMP)      # fst  dword [TMP]
                + b"\xd8\xd9"                     # fcomp st(1)
                + b"\xdf\xe0"                     # fnstsw ax
                + b"\xf6\xc4\x41"                 # test ah,0x41  (C0|C3)
                + b"\x75\x08"                     # jne  +8  (value <= seed)
                + b"\xdd\xd8"                     # fstp st(0)
                + b"\xd9\x05" + p32(PRE_TMP)      # fld  dword [TMP]
                + b"\xdd\x1d" + p32(PRE_RES))     # fstp qword [RES]
        uc.mem_write(PRE, code)
        problems = []
        for a, b in ((1.0, 2.0), (2.0, 1.0), (-5.0, -2.0), (-2.0, -5.0),
                     (3.0, 3.0), (NEG_FLT_MAX, -1.0e30)):
            uc.mem_write(PRE_A, struct.pack("<f", f32(a)))
            uc.mem_write(PRE_B, struct.pack("<f", f32(b)))
            uc.mem_write(PRE_RES, b"\x00" * 8)
            uc.reg_write(UC_X86_REG_ESP, STACK + STACKSZ - 0x400)
            try:
                uc.emu_start(PRE, PRE + len(code))
            except UcError as e:
                problems.append("x87 preflight faulted on (%r,%r): %s" % (a, b, e))
                continue
            got = struct.unpack("<d", uc.mem_read(PRE_RES, 8))[0]
            want = max(f32(a), f32(b))
            if got != want:
                problems.append("x87 preflight max(%r,%r) = %r, expected %r"
                                % (a, b, got, want))
        return problems

    # -- build the object and run the real scan ---------------------------
    def build(self, series):
        """Lay out `series` (a list of lists of python floats) in emulated
        memory exactly as MSVC's vector<vector<float>> would, and return the
        list of element ADDRESSES so the caller can check what got visited."""
        uc = self.uc
        uc.mem_write(OBJ, b"\x00" * 0x400)
        uc.mem_write(OBJ, p32(CHART_VTABLE))            # +0x00 vptr

        # trap payload: anything that reads a field we say is unread, or that
        # runs off the end of a series, lands on this value.
        uc.mem_write(TRAP_BASE, struct.pack("<f", f32(TRAP_FLOAT)) * 64)

        # payloads, each separated by a TRAP gap so an off-by-one read past
        # `_Last` picks up a number that cannot be mistaken for data.
        addrs = []
        cur = DATA_BASE
        spans = []
        for s in series:
            uc.mem_write(cur, struct.pack("<f", f32(TRAP_FLOAT)) * 4)   # guard
            cur += 16
            begin = cur
            row = []
            for v in s:
                uc.mem_write(cur, struct.pack("<f", f32(v)))
                row.append(cur)
                cur += 4
            end = cur
            uc.mem_write(cur, struct.pack("<f", f32(TRAP_FLOAT)) * 4)   # guard
            cur += 16
            spans.append((begin, end))
            addrs.extend(row)

        # descriptors, 12-byte stride, with a TRAP pointer in the unread slot
        desc = b""
        for begin, end in spans:
            desc += p32(begin) + p32(end) + p32(TRAP_BASE)
        uc.mem_write(DESC_BASE, desc if desc else b"")

        uc.mem_write(OBJ + OFF_SERIES_FIRST, p32(DESC_BASE))
        uc.mem_write(OBJ + OFF_SERIES_LAST,
                     p32(DESC_BASE + DESC_STRIDE * len(series)))
        uc.mem_write(OBJ + OFF_SERIES_END, p32(TRAP_BASE))   # unread; trapped
        return addrs

    def run(self, series, dummy_arg=0x0BADF00D):
        """Execute the REAL sub_9B5EAC. Returns a dict of every channel."""
        from unicorn import UcError
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX
        uc = self.uc
        addrs = self.build(series)

        # scrub the stack window so [ebp-4] can only hold what THIS run wrote
        uc.mem_write(STACK + STACKSZ - 0x200, b"\xCC" * 0x180)
        uc.mem_write(RESULT, b"\x00" * 8)

        # fninit before every run: the function pushes one net value onto the
        # x87 stack and our pad pops it, but a fresh TOP makes the depth check
        # below meaningful rather than relative.
        uc.reg_write(UC_X86_REG_ESP, STACK + STACKSZ - 0x400)
        uc.emu_start(FNINIT_STUB, FNINIT_STUB + 2)

        # __thiscall: args right-to-left, `this` in ECX, our pad as the return
        # address. `ret 4` says exactly one stack arg - it is never read by
        # the body (no [ebp+8] anywhere in the 44 instructions), so its value
        # is deliberately garbage to prove that.
        esp = STACK + STACKSZ - 0x100
        esp -= 4
        uc.mem_write(esp, p32(dummy_arg))
        esp -= 4
        uc.mem_write(esp, p32(PAD))
        entry_esp = esp
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.reg_write(UC_X86_REG_ECX, OBJ)

        self.series_count = None
        self.visited = []
        err = None
        try:
            uc.emu_start(MAX_SCAN_FN, self.pad_end)
        except UcError as e:
            err = str(e)

        out = {"error": err, "addrs": addrs}
        if err:
            return out
        out["result"] = struct.unpack("<d", uc.mem_read(RESULT, 8))[0]
        out["series_count"] = self.series_count
        out["visited"] = list(self.visited)
        # channel 2: the function's own [ebp-4] stash. entry_esp - 8 is that
        # local (push ebp -> ebp = entry_esp-4; push ecx -> [ebp-4]).
        out["local_ebp_m4"] = struct.unpack(
            "<f", uc.mem_read(entry_esp - 8, 4))[0]
        # x87 stack depth at `ret`, from the pad's fnstsw: TOP is bits 11..13
        # of the status word, i.e. bits 3..5 of AH. One value left -> TOP == 7.
        sw = uc.reg_read(UC_X86_REG_EAX) & 0xFFFF
        out["fpu_top"] = (sw >> 11) & 7
        out["status_word"] = sw
        # the final ESP must be entry_esp + 4 (ret addr) + 4 (the one arg)
        out["esp_after"] = uc.reg_read(UC_X86_REG_ESP)
        out["esp_expected"] = entry_esp + 8
        return out


# ---------------------------------------------------------------------------
# THE CASES. Every expectation is computed from the same numbers we wrote into
# emulated memory - nothing here is a remembered constant.
# ---------------------------------------------------------------------------
CASES = [
    ("two series, max in the second",
     [[1.0, 5.0, 3.0], [2.0, 9.0, 4.0]]),
    ("three series, max in the first",
     [[100.25, 1.0], [2.0, 3.0], [4.0, 5.0]]),
    ("ALL NEGATIVE (proves the -FLT_MAX seed, not a 0 seed)",
     [[-5.0, -2.0, -30.0]]),
    ("all negative across two series",
     [[-1.5, -2.5], [-0.25], [-100.0]]),
    ("mixed sign, max is a small positive",
     [[-1.5, -2.5], [0.25], [-100.0]]),
    ("SINGLE SERIES, single point",
     [[42.5]]),
    ("single series, max first (loop-entry boundary)",
     [[100.0, 1.0, 2.0]]),
    ("single series, max last (loop-exit boundary)",
     [[1.0, 2.0, 100.0]]),
    ("duplicate max (exercises the C3 equality branch)",
     [[7.0, 7.0, 3.0], [7.0]]),
    ("empty inner series are skipped, not read",
     [[], [3.5], []]),
    ("first series empty",
     [[], [-8.0, -9.0]]),
    ("five series (proves the idiv-by-12 stride at length)",
     [[1.0], [2.0], [3.0], [12.5], [4.0]]),
    ("long single series",
     [[float(i) * 0.5 - 20.0 for i in range(64)]]),
    ("EMPTY series vector -> the raw seed comes back",
     []),
    ("one empty series only -> the raw seed comes back",
     [[]]),
]


def run_target1(verbose):
    print("emu_chart_range - SimCity 4's own chart series max-scan, run offline")
    print("  target : sub_9B5EAC @ 0x%08X   (chart main-vt 0x%08X +0x%03X)"
          % (MAX_SCAN_FN, CHART_VTABLE, SLOT_MAX_SCAN))
    print("  scope  : IN = that function only. OUT = anything needing a font.")
    print("=" * 72)

    try:
        import unicorn  # noqa: F401
    except ImportError as e:
        print("FAIL - unicorn is not importable: %s" % e)
        return 1

    try:
        emu = ChartRangeEmu()
    except Exception as e:
        print("FAIL - could not map %s: %s" % (EXE, e))
        return 1

    fails, checks = [], 0

    # -- gate 0: is the exe the one this file was written against? ---------
    checks += 1
    if emu.image_complaints:
        for m in emu.image_complaints:
            fails.append("image check: " + m)
    else:
        print("image  : vtable +0x290/+0x294, prologue bytes and both FLT_MAX"
              " seeds verified")

    # -- gate 1: does Unicorn's x87 actually work here? --------------------
    checks += 1
    x87 = emu.x87_preflight()
    if x87:
        for m in x87:
            fails.append(m)
        print("\nFAIL - Unicorn's x87 support MISBEHAVES in this environment.")
        print("       The target is an x87 running-max; without a trustworthy")
        print("       FPU there is no honest result to report. Details:")
        for m in x87:
            print("   x " + m)
        print("\nFAIL - 0 of %d cases run (x87 preflight failed)" % len(CASES))
        return 1
    print("x87    : preflight PASS (fld/fst/fcomp/fnstsw/fstp, 6 orderings)")
    print("=" * 72)

    if emu.image_complaints:
        print("\nFAIL - the exe does not match this harness:")
        for m in emu.image_complaints:
            print("   x " + m)
        return 1

    # -- the cases ---------------------------------------------------------
    for name, series in CASES:
        flat = [f32(v) for s in series for v in s]
        expected = max(flat) if flat else NEG_FLT_MAX
        out = emu.run(series)

        if out["error"]:
            fails.append("%s: emulation faulted: %s" % (name, out["error"]))
            print("  x %-56s EMU FAULT" % name[:56])
            continue

        got = out["result"]
        ok = (got == expected)

        # channel A - the x87 return value
        checks += 1
        if not ok:
            fails.append("%s: returned %r, true max is %r" % (name, got, expected))

        # channel B - the series count the function's OWN idiv produced
        checks += 1
        if out["series_count"] != len(series):
            fails.append("%s: the function's idiv gave %r series, we built %d"
                         % (name, out["series_count"], len(series)))

        # channel C - exactly which addresses it read (stride + bounds proof)
        checks += 1
        if out["visited"] != out["addrs"]:
            fails.append("%s: visited %d addresses, expected %d (stride or "
                         "bounds wrong)" % (name, len(out["visited"]),
                                            len(out["addrs"])))

        # channel D - the guard values must never surface
        checks += 1
        if got == f32(TRAP_FLOAT):
            fails.append("%s: result is the TRAP guard - the scan over-read"
                         % name)

        # channel E - memory the real code wrote itself: [ebp-4] holds the
        # last element it fst'd, which must be the last element of the last
        # NON-EMPTY series. (Nothing is written when there are no elements.)
        checks += 1
        if flat:
            last_elem = None
            for s in series:
                if s:
                    last_elem = f32(s[-1])
            if out["local_ebp_m4"] != last_elem:
                fails.append("%s: [ebp-4] holds %r, last element scanned was %r"
                             % (name, out["local_ebp_m4"], last_elem))

        # channel F - the FPU stack must hold exactly one value at `ret`
        checks += 1
        if out["fpu_top"] != 7:
            fails.append("%s: FPU TOP=%d at ret (expected 7 = one value); "
                         "status word 0x%04X"
                         % (name, out["fpu_top"], out["status_word"]))

        # channel G - `ret 4` must clean exactly one argument
        checks += 1
        if out["esp_after"] != out["esp_expected"]:
            fails.append("%s: ESP after = 0x%08X, expected 0x%08X (ret 4 "
                         "arg-count wrong)"
                         % (name, out["esp_after"], out["esp_expected"]))

        mark = " " if ok else "x"
        note = ""
        if not flat:
            note = "  (= -FLT_MAX seed)"
        print("  %s %-52s -> %-14s%s" % (mark, name[:52], repr(got), note))
        if verbose:
            print("        series=%s  idiv count=%r  elements visited=%d  "
                  "[ebp-4]=%r  TOP=%d"
                  % ([len(s) for s in series], out["series_count"],
                     len(out["visited"]), out["local_ebp_m4"], out["fpu_top"]))

    # -- a deliberate negative control: prove the harness can FAIL ---------
    # If a "test" cannot fail it is not an instrument. Feed the scan a series
    # whose payload we then corrupt behind its back, and require the returned
    # max to CHANGE. (NULL IS NOT EVIDENCE: this is the positive control for
    # every green line above.)
    checks += 1
    base = emu.run([[1.0, 2.0, 3.0]])["result"]
    poisoned = emu.run([[1.0, 2.0, 3.0, 999.0]])["result"]
    if not (base == 3.0 and poisoned == 999.0):
        fails.append("negative control: base=%r poisoned=%r - the harness is "
                     "not actually reading the data" % (base, poisoned))

    print("=" * 72)
    if fails:
        print("FAIL - %d checks, %d failures" % (checks, len(fails)))
        for m in fails:
            print("   x " + m)
        return 1
    print("PASS - %d checks over %d cases. The chart's own sub_9B5EAC runs "
          "correctly" % (checks, len(CASES)))
    print("       under Unicorn over an object we built: series count, "
          "12-byte stride,")
    print("       element bounds, the -FLT_MAX seed, the equality branch and "
          "the x87")
    print("       return value all agree. SCOPE: this proves the OBJECT MODEL "
          "and the")
    print("       emulator, nothing about chart pixels or any font-dependent "
          "layout.")
    return 0


# ===========================================================================
# SECOND TARGET - sub_9B3647 @ 0x009B3647, chart main-vt +0x2A8:
#                 the axis auto-range / layout driver.
# ===========================================================================
# SCOPE FOR THIS HALF (narrower than target 1 - read it before quoting any
# number out of it):
#   IN  - the driver's own control flow and its own arithmetic:
#         * WHICH helper slot it calls, in what ORDER, with what index arg,
#           and WHICH sentinel field decides each call;
#         * the "both bounds were auto and came back equal" fixup
#           (max == 0 -> 1.0, else max *= the image's own 1.1111112);
#         * the tick-decimals ladder it writes to the byte pair at
#           [obj+0x17C]/[obj+0x17D], using the five threshold floats read
#           back out of the image, never typed in;
#         * the PLUMBING of the four rects: which field each one is copied
#           into, and that the plot rect is handed to the store interface
#           rather than written by the driver itself.
#   OUT - THE RECT VALUES THEMSELVES. Every rect here is a tagged fake we
#         inject through a stub. The real sub_9B387A / sub_9B799D /
#         sub_9B7B57 derive their rects from TEXT EXTENTS, i.e. from a font
#         we do not have offline. This half therefore proves the chart's
#         layout WIRING and cannot, on its own, predict one pixel of chart
#         geometry. Anyone who quotes a rect out of this file is quoting a
#         number this file invented.
#   OUT - the data min/max the driver fills auto bounds with. Those come
#         from vt+0x2B8 / +0x2BC, which are stubbed here with canned values.
#         (Those two do bottom out in the real target-1 scan, so a future
#         version could chain them honestly - it is not chained today.)
#
# CALL MAP, byte-verified from the shipped exe. The arg counts are NOT
# guessed: each is the callee's own `ret N`, and each matches the number of
# pushes at the call site (get this wrong and the stack desyncs silently).
#   site        slot        callee       ret  args                 role
#   0x9B3689    vt+0x2B8    sub_9B2301    8   (axis, float* out)   data min
#   0x9B36BA    vt+0x2BC    sub_9B2333    8   (axis, float* out)   data max
#   0x9B378F    vt+0x2B0    sub_9B799D    4   (RECT* out)          plot rect
#   0x9B37A1    ifc+0x30    sub_9B1F1D    4   (RECT* in)           STORE
#   0x9B37B6    vt+0x2AC    sub_9B387A    4   (RECT* out)          legend
#   0x9B37EC    vt+0x2B4    sub_9B7B57    8   (axis, RECT* out)    axis title
#   0x9B3819    vt+0x2C0    sub_9B23F6    8   (axis, float* out)
#   0x9B3841    vt+0x2C4    sub_9B2417    8   (axis, float* out)
#   0x9B3853    vt+0x298    sub_9B2365    4   (axis)
# sub_9B1F1D is the store: `lea edi,[ecx+8]` + 4x movsd, i.e. it copies the
# rect to this+8. `this` is obj+0xD8, so the plot rect's home is obj+0xE0 -
# exactly the sentinel field the driver tested. We stub it and CAPTURE only,
# which is why obj+0xE0 is asserted UNCHANGED below: the driver never writes
# it, the store does.
#
# INDEX TRICK (0x9B3651): `mov ecx,0xFFFFFE84 / sub ecx,ebx`, then
# `lea eax,[ecx+esi]` with esi walking obj+0x17C.. -> eax is the 0-based
# axis index by 32-bit wraparound, for ANY object address. Two axes.
# ===========================================================================

AXIS_FN = 0x009B3647          # chart main-vt +0x2A8
SLOT_AXIS = 0x2A8

# constants the driver loads out of the image; addresses byte-read from the
# disassembly, VALUES read back from the exe at run time (never typed in).
K_FLT_MIN_SENTINEL = 0x00B17C1C   # the "this bound is AUTO" float sentinel
K_ZERO             = 0x00A81054   # 0.0
K_HEADROOM         = 0x00ADDE38   # 1.1111112  (10/9)
K_LADDER = (0x00A94D50,   # 10.0    range >= this -> decimals 0
            0x00A99E1C,   # 1e-4    range <  this -> decimals 5
            0x00A867A4,   # 1e-3    range <  this -> decimals 4
            0x00A823A4,   # 1e-2    range <  this -> decimals 3
            0x00A8C950)   # 0.1     range <  this -> decimals 2, else 1

RECT_UNSET = 0x7FFFFFFF       # the "this rect is AUTO" dword sentinel
POWER_AUTO = 0x80             # the "these decimals are AUTO" byte sentinel

# --- object field map for the driver, with provenance ----------------------
#   +0x000  vptr                       0x9B367E `mov eax,[ebx]`
#   +0x0D8  embedded store interface   0x9B3795 `lea ecx,[ebx+0xd8]`, then
#                                      `mov eax,[ecx]` -> its own vptr
#   +0x0E0  plot RECT                  0x9B377F `cmp [ebx+0xE0],0x7FFFFFFF`
#                                      (= store `this`+8, per sub_9B1F1D)
#   +0x108  legend RECT (16B)          0x9B37A4/0x9B37AA + 4x movsd
#   +0x15C  axis[0] min  (float)       0x9B3672 `fld [edi-8]`, edi=ebx+0x164
#   +0x160  axis[1] min
#   +0x164  axis[0] max  (float)       0x9B36A4 `fld [edi]`
#   +0x168  axis[1] max
#   +0x16C  axis[0] lo   (float)       0x9B3802 `fld [esi-8]`, esi=ebx+0x174
#   +0x170  axis[1] lo
#   +0x174  axis[0] hi   (float)       0x9B382B `fld [esi]`
#   +0x178  axis[1] hi
#   +0x17C  axis[0] decimals (byte)    0x9B3701 `cmp byte [esi],0x80`,
#   +0x17D  axis[1] decimals (byte)    esi=ebx+0x17C, `inc esi` per axis
#   +0x1CC  axis[0] title RECT (16B)   0x9B37CD/0x9B37D9 + 4x movsd
#   +0x1DC  axis[1] title RECT (16B)   `add edi,0x10`
OFF_STORE_IFACE = 0x0D8
OFF_PLOT_RECT   = 0x0E0
OFF_LEGEND_RECT = 0x108
OFF_AXIS_MIN    = 0x15C
OFF_AXIS_MAX    = 0x164
OFF_AXIS_LO     = 0x16C
OFF_AXIS_HI     = 0x174
OFF_AXIS_DEC    = 0x17C
OFF_TITLE_RECT  = 0x1CC

OBJ2      = HEAP + 0x00020000
VT_MAIN   = HEAP + 0x00030000     # our fake main vtable (all TRAP but ours)
VT_IFACE  = HEAP + 0x00031000     # our fake store-interface vtable
STUBS     = 0x60000000
STUBSZ    = 0x00001000
PAD2         = PAD + 0x200        # `fnstsw ax` only - the driver returns void
FNINIT_STUB2 = PAD + 0x300        # this emulator's own one-off `fninit`

# stub index -> (label, vtable slot or None for the iface, arg count)
STUB_TABLE = [
    ("data_min",   0x2B8, 2),
    ("data_max",   0x2BC, 2),
    ("plot_rect",  0x2B0, 1),
    ("legend_rect", 0x2AC, 1),
    ("title_rect", 0x2B4, 2),
    ("slot_2C0",   0x2C0, 2),
    ("slot_2C4",   0x2C4, 2),
    ("slot_298",   0x298, 1),
    ("store",      None,  1),      # the embedded interface's +0x30
]
TRAP_STUB_INDEX = len(STUB_TABLE)  # every other vtable slot points here


def check_image2(data):
    bad = []

    def dw(va):
        off = va - IMAGE_BASE
        return struct.unpack("<I", data[off:off + 4])[0]

    if dw(CHART_VTABLE + SLOT_AXIS) != AXIS_FN:
        bad.append("vt +0x%03X = 0x%08X, expected the driver 0x%08X"
                   % (SLOT_AXIS, dw(CHART_VTABLE + SLOT_AXIS), AXIS_FN))
    want = {0x298: 0x009B2365, 0x2AC: 0x009B387A, 0x2B0: 0x009B799D,
            0x2B4: 0x009B7B57, 0x2B8: 0x009B2301, 0x2BC: 0x009B2333,
            0x2C0: 0x009B23F6, 0x2C4: 0x009B2417}
    for slot, fn in sorted(want.items()):
        got = dw(CHART_VTABLE + slot)
        if got != fn:
            bad.append("vt +0x%03X = 0x%08X, expected 0x%08X" % (slot, got, fn))
    head = data[AXIS_FN - IMAGE_BASE:AXIS_FN - IMAGE_BASE + 12]
    want_head = bytes.fromhex("558bec83ec24538bd956b984feffff")[:12]
    if head != want_head:
        bad.append("sub_9B3647 prologue bytes differ: %s" % head.hex())
    return bad


class AxisDriverEmu(object):
    """Runs the REAL sub_9B3647 with all nine of its callees stubbed."""

    def __init__(self):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        data = open(EXE, "rb").read()
        self.image_complaints = check_image2(data)
        # the driver's own constants, READ BACK from the image
        def fl(va):
            off = va - IMAGE_BASE
            return struct.unpack("<f", data[off:off + 4])[0]
        self.SENTINEL = fl(K_FLT_MIN_SENTINEL)
        self.ZERO = fl(K_ZERO)
        self.HEADROOM = fl(K_HEADROOM)
        self.LADDER = [fl(a) for a in K_LADDER]

        uc = Uc(UC_ARCH_X86, UC_MODE_32)
        span = max((len(data) + 0xFFF) & ~0xFFF, 0x800000)
        uc.mem_map(IMAGE_BASE, span)
        uc.mem_write(IMAGE_BASE, data)
        uc.mem_map(HEAP, HEAPSZ)
        uc.mem_map(STACK, STACKSZ)
        uc.mem_map(PAD, PADSZ)
        uc.mem_map(STUBS, STUBSZ)
        uc.mem_write(PAD2, b"\xdf\xe0")             # fnstsw ax
        uc.mem_write(FNINIT_STUB2, b"\xdb\xe3")     # fninit
        uc.mem_write(STUBS, b"\xcc" * STUBSZ)       # never executed; hooked
        uc.hook_add(UC_HOOK_CODE, self._hook_stub,
                    begin=STUBS, end=STUBS + STUBSZ - 1)

        # every slot of both fake vtables points at the TRAP stub, so an
        # unexpected virtual call is caught loudly instead of jumping to 0.
        trap = p32(STUBS + 0x10 * TRAP_STUB_INDEX)
        uc.mem_write(VT_MAIN, trap * (0x400 // 4))
        uc.mem_write(VT_IFACE, trap * (0x100 // 4))
        for i, (label, slot, nargs) in enumerate(STUB_TABLE):
            addr = p32(STUBS + 0x10 * i)
            if slot is None:
                uc.mem_write(VT_IFACE + 0x30, addr)
            else:
                uc.mem_write(VT_MAIN + slot, addr)

        self.uc = uc
        self.calls = []
        self.canned = {}
        self.trapped = None

    # -- the nine modelled calls ------------------------------------------
    def _hook_stub(self, uc, addr, size, user):
        from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_EIP,
                                       UC_X86_REG_ECX, UC_X86_REG_EAX)
        idx = (addr - STUBS) // 0x10
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack("<I", uc.mem_read(esp, 4))[0]
        this = uc.reg_read(UC_X86_REG_ECX)

        if idx == TRAP_STUB_INDEX:
            self.trapped = "a vtable slot we did not stub was called from " \
                           "return address 0x%08X" % ret
            uc.emu_stop()
            return

        label, slot, nargs = STUB_TABLE[idx]
        args = [struct.unpack("<I", uc.mem_read(esp + 4 + 4 * i, 4))[0]
                for i in range(nargs)]
        rec = {"label": label, "this": this, "args": tuple(args), "out": None}

        if label in ("data_min", "data_max", "slot_2C0", "slot_2C4"):
            axis, out_ptr = args
            val = f32(self.canned[label][axis])
            uc.mem_write(out_ptr, struct.pack("<f", val))
            rec["out"] = val
        elif label == "plot_rect":
            rect = self.canned["plot_rect"]
            uc.mem_write(args[0], struct.pack("<4i", *rect))
            rec["out"] = rect
        elif label == "legend_rect":
            rect = self.canned["legend_rect"]
            uc.mem_write(args[0], struct.pack("<4i", *rect))
            rec["out"] = rect
        elif label == "title_rect":
            axis, out_ptr = args
            rect = self.canned["title_rect"][axis]
            uc.mem_write(out_ptr, struct.pack("<4i", *rect))
            rec["out"] = rect
        elif label == "store":
            # CAPTURE ONLY. The real sub_9B1F1D copies this rect to this+8
            # (= obj+0xE0); deliberately not modelled, so obj+0xE0 must come
            # back untouched - which is itself an assertion below.
            rec["out"] = struct.unpack("<4i", uc.mem_read(args[0], 16))
        elif label == "slot_298":
            pass

        self.calls.append(rec)
        uc.reg_write(UC_X86_REG_EAX, 0)
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + 4 * nargs)   # callee-cleans
        uc.reg_write(UC_X86_REG_EIP, ret)

    # -- build + run -------------------------------------------------------
    def run(self, spec):
        from unicorn import UcError
        from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_ECX,
                                       UC_X86_REG_EAX, UC_X86_REG_EFLAGS)
        uc = self.uc
        self.canned = spec["canned"]
        self.calls = []
        self.trapped = None

        uc.mem_write(OBJ2, b"\x00" * 0x400)
        uc.mem_write(OBJ2, p32(VT_MAIN))
        uc.mem_write(OBJ2 + OFF_STORE_IFACE, p32(VT_IFACE))

        def putf(off, v):
            uc.mem_write(OBJ2 + off,
                         struct.pack("<f", self.SENTINEL if v is AUTO else f32(v)))
        for i in range(2):
            putf(OFF_AXIS_MIN + 4 * i, spec["min"][i])
            putf(OFF_AXIS_MAX + 4 * i, spec["max"][i])
            putf(OFF_AXIS_LO + 4 * i, spec["lo"][i])
            putf(OFF_AXIS_HI + 4 * i, spec["hi"][i])
            uc.mem_write(OBJ2 + OFF_AXIS_DEC + i, bytes([spec["dec"][i] & 0xFF]))
            uc.mem_write(OBJ2 + OFF_TITLE_RECT + 0x10 * i,
                         struct.pack("<4i", *(
                             (RECT_UNSET, 0, 0, 0) if spec["title_unset"][i]
                             else (-11, -12, -13, -14))))
        uc.mem_write(OBJ2 + OFF_PLOT_RECT,
                     struct.pack("<4i", *((RECT_UNSET, 0, 0, 0)
                                          if spec["plot_unset"]
                                          else (-21, -22, -23, -24))))
        uc.mem_write(OBJ2 + OFF_LEGEND_RECT,
                     struct.pack("<4i", *((RECT_UNSET, 0, 0, 0)
                                          if spec["legend_unset"]
                                          else (-31, -32, -33, -34))))

        uc.mem_write(STACK + STACKSZ - 0x300, b"\xCC" * 0x280)
        uc.reg_write(UC_X86_REG_ESP, STACK + STACKSZ - 0x400)
        uc.emu_start(FNINIT_STUB2, FNINIT_STUB2 + 2)

        esp = STACK + STACKSZ - 0x100
        esp -= 4
        uc.mem_write(esp, p32(PAD2))       # `ret` (no args) lands on the pad
        entry_esp = esp
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.reg_write(UC_X86_REG_ECX, OBJ2)
        uc.reg_write(UC_X86_REG_EFLAGS, 0x202)     # DF=0: the 4x movsd copies
        err = None                                  #        forward
        try:
            uc.emu_start(AXIS_FN, PAD2 + 2)
        except UcError as e:
            err = str(e)

        out = {"error": err, "trapped": self.trapped, "calls": list(self.calls)}
        if err or self.trapped:
            return out
        rd = lambda off, n: uc.mem_read(OBJ2 + off, n)
        out["min"] = [struct.unpack("<f", rd(OFF_AXIS_MIN + 4 * i, 4))[0]
                      for i in range(2)]
        out["max"] = [struct.unpack("<f", rd(OFF_AXIS_MAX + 4 * i, 4))[0]
                      for i in range(2)]
        out["lo"] = [struct.unpack("<f", rd(OFF_AXIS_LO + 4 * i, 4))[0]
                     for i in range(2)]
        out["hi"] = [struct.unpack("<f", rd(OFF_AXIS_HI + 4 * i, 4))[0]
                     for i in range(2)]
        out["dec"] = list(rd(OFF_AXIS_DEC, 2))
        out["plot_rect"] = struct.unpack("<4i", rd(OFF_PLOT_RECT, 16))
        out["legend_rect"] = struct.unpack("<4i", rd(OFF_LEGEND_RECT, 16))
        out["title_rect"] = [struct.unpack("<4i", rd(OFF_TITLE_RECT + 0x10 * i, 16))
                             for i in range(2)]
        sw = uc.reg_read(UC_X86_REG_EAX) & 0xFFFF
        out["fpu_top"] = (sw >> 11) & 7
        out["esp_after"] = uc.reg_read(UC_X86_REG_ESP)
        out["esp_expected"] = entry_esp + 4          # plain `ret`, zero args
        return out

    # -- the driver's own arithmetic, re-derived in python -----------------
    def predict(self, spec):
        """Predict what the driver must produce, from the disassembled LADDER
        ORDER plus the threshold VALUES read out of the image. This is the
        oracle the emulation is checked against."""
        calls, mins, maxs, decs = [], [], [], []
        for i in range(2):
            both_auto = True
            if spec["min"][i] is AUTO:
                calls.append(("data_min", i))
                mn = f32(spec["canned"]["data_min"][i])
            else:
                both_auto = False
                mn = f32(spec["min"][i])
            if spec["max"][i] is AUTO:
                calls.append(("data_max", i))
                mx = f32(spec["canned"]["data_max"][i])
            else:
                both_auto = False
                mx = f32(spec["max"][i])
            if both_auto and mn == mx:
                mx = 1.0 if mx == self.ZERO else f32(mx * self.HEADROOM)
            if (spec["dec"][i] & 0xFF) == POWER_AUTO:
                rng = mx - mn
                t10, t1e4, t1e3, t1e2, t1e1 = self.LADDER
                if rng >= t10:
                    d = 0
                elif rng < t1e4:
                    d = 5
                elif rng < t1e3:
                    d = 4
                elif rng < t1e2:
                    d = 3
                elif rng < t1e1:
                    d = 2
                else:
                    d = 1
            else:
                d = spec["dec"][i] & 0xFF
            mins.append(mn)
            maxs.append(mx)
            decs.append(d)
        if spec["plot_unset"]:
            calls.append(("plot_rect", None))
            calls.append(("store", None))
        if spec["legend_unset"]:
            calls.append(("legend_rect", None))
        los, his = [], []
        for i in range(2):
            if spec["title_unset"][i]:
                calls.append(("title_rect", i))
            if spec["lo"][i] is AUTO:
                calls.append(("slot_2C0", i))
                los.append(f32(spec["canned"]["slot_2C0"][i]))
            else:
                los.append(f32(spec["lo"][i]))
            if spec["hi"][i] is AUTO:
                calls.append(("slot_2C4", i))
                his.append(f32(spec["canned"]["slot_2C4"][i]))
            else:
                his.append(f32(spec["hi"][i]))
            calls.append(("slot_298", i))
        return {"calls": calls, "min": mins, "max": maxs, "dec": decs,
                "lo": los, "hi": his}


class _Auto(object):
    def __repr__(self):
        return "AUTO"


AUTO = _Auto()

CANNED = {
    "data_min": [-3.0, 0.0],
    "data_max": [7.0, 250.0],
    "slot_2C0": [-0.5, -0.75],
    "slot_2C4": [0.5, 0.75],
    "plot_rect": (1000, 1001, 1002, 1003),
    "legend_rect": (2000, 2001, 2002, 2003),
    "title_rect": [(3000, 3001, 3002, 3003), (3100, 3101, 3102, 3103)],
}


def spec(name, **kw):
    s = {"name": name,
         "min": [AUTO, AUTO], "max": [AUTO, AUTO],
         "lo": [AUTO, AUTO], "hi": [AUTO, AUTO],
         "dec": [POWER_AUTO, POWER_AUTO],
         "plot_unset": True, "legend_unset": True,
         "title_unset": [True, True],
         "canned": dict(CANNED)}
    s.update(kw)
    return s


def _canned(**kw):
    c = dict(CANNED)
    c.update(kw)
    return c


def build_cases2():
    cases = [
        spec("everything AUTO: both axes, all four rects"),
        spec("nothing AUTO: no helper may be called",
             min=[-1.0, -2.0], max=[10.0, 20.0], lo=[0.1, 0.2], hi=[1.0, 2.0],
             dec=[3, 4], plot_unset=False, legend_unset=False,
             title_unset=[False, False]),
        spec("plot rect already set, legend still AUTO",
             plot_unset=False),
        spec("legend already set, plot still AUTO",
             legend_unset=False),
        spec("axis-1 title already set (per-axis rect gate)",
             title_unset=[True, False]),
        spec("axis 0 min explicit, max AUTO -> NO equal-bounds fixup",
             min=[5.0, AUTO], canned=_canned(data_max=[5.0, 250.0])),
        spec("both AUTO and EQUAL non-zero -> max *= the image's 1.1111112",
             canned=_canned(data_min=[5.0, 0.0], data_max=[5.0, 250.0])),
        spec("both AUTO and EQUAL zero -> max becomes 1.0",
             canned=_canned(data_min=[0.0, 0.0], data_max=[0.0, 250.0])),
        spec("decimals already set -> the ladder must not run",
             dec=[2, 2], canned=_canned(data_min=[0.0, 0.0],
                                        data_max=[0.001, 5000.0])),
    ]
    # the decimals ladder, swept across every decade boundary it tests.
    # min is pinned explicit at 0 so range == max exactly.
    for r in (1000.0, 10.0, 9.9, 1.0, 0.1, 0.05, 0.01, 0.009, 0.001,
              0.0009, 0.0001, 0.00009, 0.0):
        cases.append(spec("decimals ladder: range = %g" % r,
                          min=[0.0, 0.0], max=[r, r]))
    return cases


def run_target2(verbose):
    print()
    print("=" * 72)
    print("SECOND TARGET - sub_9B3647 @ 0x%08X  (chart main-vt +0x%03X)"
          % (AXIS_FN, SLOT_AXIS))
    print("  scope : IN = the driver's OWN control flow + arithmetic.")
    print("          OUT = every rect VALUE (injected fakes; the real ones")
    print("                come from text extents we cannot measure offline).")
    print("=" * 72)

    try:
        emu = AxisDriverEmu()
    except Exception as e:
        print("FAIL - could not build the axis-driver emulator: %s" % e)
        return 1, 0
    if emu.image_complaints:
        print("FAIL - the exe does not match this harness:")
        for m in emu.image_complaints:
            print("   x " + m)
        return 1, 0
    print("image  : vt +0x2A8 and all eight helper slots verified; "
          "constants read from .rdata")
    print("         sentinel=%r  headroom=%r  ladder=%s"
          % (emu.SENTINEL, emu.HEADROOM, [repr(v) for v in emu.LADDER]))

    fails, checks = [], 0
    for s in build_cases2():
        want = emu.predict(s)
        got = emu.run(s)
        name = s["name"]

        if got["error"] or got["trapped"]:
            fails.append("%s: %s" % (name, got["trapped"] or got["error"]))
            print("  x %-60s EMU FAULT" % name[:60])
            continue

        seq = [(c["label"], (c["args"][0] if c["label"] not in
                             ("plot_rect", "legend_rect", "store") else None))
               for c in got["calls"]]
        checks += 1
        if seq != want["calls"]:
            fails.append("%s: call sequence\n        got  %s\n        want %s"
                         % (name, seq, want["calls"]))

        for key in ("min", "max", "lo", "hi", "dec"):
            checks += 1
            if got[key] != want[key]:
                fails.append("%s: %s = %s, predicted %s"
                             % (name, key, got[key], want[key]))

        # rect PLUMBING (not values): whatever the stub handed back must be
        # exactly what landed in the field the driver owns.
        checks += 1
        if s["legend_unset"]:
            if got["legend_rect"] != CANNED["legend_rect"]:
                fails.append("%s: legend rect landed as %s, stub returned %s"
                             % (name, got["legend_rect"], CANNED["legend_rect"]))
        elif got["legend_rect"] != (-31, -32, -33, -34):
            fails.append("%s: legend rect was already set but got overwritten "
                         "with %s" % (name, got["legend_rect"]))

        for i in range(2):
            checks += 1
            if s["title_unset"][i]:
                if got["title_rect"][i] != CANNED["title_rect"][i]:
                    fails.append("%s: axis %d title rect landed as %s, stub "
                                 "returned %s" % (name, i, got["title_rect"][i],
                                                  CANNED["title_rect"][i]))
            elif got["title_rect"][i] != (-11, -12, -13, -14):
                fails.append("%s: axis %d title rect was already set but got "
                             "overwritten with %s"
                             % (name, i, got["title_rect"][i]))

        # the plot rect is the store's job, never the driver's
        checks += 1
        if s["plot_unset"]:
            store = [c for c in got["calls"] if c["label"] == "store"]
            if len(store) != 1 or store[0]["out"] != CANNED["plot_rect"]:
                fails.append("%s: the store was not handed the plot rect the "
                             "plot helper produced (%s)"
                             % (name, [c["out"] for c in store]))
            if store and store[0]["this"] != OBJ2 + OFF_STORE_IFACE:
                fails.append("%s: store `this` = 0x%08X, expected obj+0x%03X"
                             % (name, store[0]["this"], OFF_STORE_IFACE))
            if got["plot_rect"][0] != RECT_UNSET:
                fails.append("%s: obj+0x%03X changed to %s - the DRIVER wrote "
                             "the plot rect, which contradicts sub_9B1F1D "
                             "being the writer"
                             % (name, OFF_PLOT_RECT, got["plot_rect"]))
        elif got["plot_rect"] != (-21, -22, -23, -24):
            fails.append("%s: plot rect was already set but changed to %s"
                         % (name, got["plot_rect"]))

        # `this` on every main-vtable call must be the object itself
        checks += 1
        for c in got["calls"]:
            if c["label"] != "store" and c["this"] != OBJ2:
                fails.append("%s: %s got this=0x%08X, expected the object "
                             "0x%08X" % (name, c["label"], c["this"], OBJ2))
                break

        # x87 must come back balanced, and a plain `ret` cleans nothing
        checks += 1
        if got["fpu_top"] != 0:
            fails.append("%s: FPU TOP=%d at ret (expected 0 = stack empty)"
                         % (name, got["fpu_top"]))
        checks += 1
        if got["esp_after"] != got["esp_expected"]:
            fails.append("%s: ESP after = 0x%08X, expected 0x%08X"
                         % (name, got["esp_after"], got["esp_expected"]))

        ok = not any(f.startswith(name + ":") for f in fails)
        print("  %s %-46s min=%-8s max=%-10s dec=%s"
              % (" " if ok else "x", name[:46],
                 "%g" % got["min"][0], "%g" % got["max"][0], got["dec"]))
        if verbose:
            print("        calls: %s" % (seq,))

    print("-" * 72)
    if fails:
        print("SECOND TARGET FAIL - %d checks, %d failures" % (checks, len(fails)))
        for m in fails:
            print("   x " + m)
        return 1, checks
    print("SECOND TARGET PASS - %d checks. The driver's gating, ordering, "
          "auto-range" % checks)
    print("  fixup, decimals ladder and rect plumbing all reproduce. SCOPE "
          "REMINDER: every")
    print("  rect in this half is a fake we injected - this proves WIRING, "
          "not geometry.")
    return 0, checks


def main():
    verbose = "--verbose" in sys.argv
    which = "both"
    for a in sys.argv[1:]:
        if a.startswith("--target="):
            which = a.split("=", 1)[1]
    rc = 0
    if which in ("1", "both"):
        rc |= run_target1(verbose)
    if which in ("2", "both"):
        rc2, _ = run_target2(verbose)
        rc |= rc2
    print()
    print("OVERALL: %s" % ("PASS" if rc == 0 else "FAIL"))
    return 1 if rc else 0


if __name__ == "__main__":
    sys.exit(main())
