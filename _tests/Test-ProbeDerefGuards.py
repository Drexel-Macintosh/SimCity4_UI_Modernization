#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Test-ProbeDerefGuards - build gate: no speculative dereference in PROBE or
DETOUR code outside a __try block (or a ProbeSafe helper).

WHY THIS EXISTS
    Four of the exception reports the game wrote between 2026-08-05 and
    2026-09-01 fault INSIDE SC4UIScale.dll, and every one of them is a
    research probe reading memory it only guessed at:

      2026-08-18 08:30 / 2026-08-31 13:08   LogBubbleCallStack   c[-5] == 0xE8
      2026-08-18 15:43 / 2026-08-18 15:44   SpGetterLog          mov esi,[ebx]

    A probe's whole job is to look at something it cannot prove is an object.
    The read may be wrong; the process going down because of it is the defect.
    Every such read belongs under __try / __except(EXCEPTION_EXECUTE_HANDLER)
    or behind a ProbeSafe helper. This gate makes the omission a build failure
    instead of a crash report.

WHAT IS A "REAL" SPECULATIVE READ (the RED set)
    A site is RED only when ALL of these hold:
      1. its shape is one of
           vptr   `*reinterpret_cast<void**>(x)`, `*reinterpret_cast<void***>(x)`,
                  `*reinterpret_cast<uintptr_t*>(x)` (const or not) used as a
                  READ (writes through the same cast - the vtable-swap
                  machinery - are counted, not gated);
           slot   an indirect call through a vtable slot: `reinterpret_cast<
                  Fn>(vt[n])(obj)` on the spot, or stored into a local and
                  called within the next few lines; identifiers ending in `vt`
                  (vt, dvt, pvt, vt0, a1vt ...) and `pv` are vtable pointers
                  by house naming;
           peek   `x[-N] == 0xHH` - sniffing call encodings backwards from a
                  word found on the stack (the LogBubbleCallStack shape);
      2. it sits in PROBE/DETOUR SCOPE: the enclosing function's name matches
         (Log|Detour|Thunk|Probe|Cap|Census|Scan) or starts with `Sp`, OR the
         function body calls `_ReturnAddress()`. Layout code walking windows
         the game just handed it (EnumChildren / GetChildWindow results,
         `w->GetID()` beside the read) is not a probe and is not gated;
      3. it is NOT inside a `__try { ... }` span (brace-matched after comments
         and strings are blanked) and NOT inside a helper whose whole body is
         one __try/__except (derived from the code: SafeReadByte, SafeRead4,
         ProbeSafe::ReadPtr/ReadBytes ...; `--allow NAME` adds more);
      4. its base identifier was NOT validated by a ProbeSafe helper in the
         same function - `x = ProbeSafe::SafeVt(..)`, `x = ProbeSafe::SafeSlot(
         ..)`, `ProbeSafe::ReadPtr(.., &x)`, `ProbeSafe::ReadBytes(.., x, n)`
         mark `x` as validated, so `reinterpret_cast<Fn>(getType)(obj)` after
         `getType = SafeSlot(vt, 7)` and `vt[3]` after `vt = SafeVt(obj)` are
         not flagged even though the call is lexically outside __try;
      5. it carries no waiver. `// deref-ok: <reason>` on the flagged line or
         the line above waives the site; waived sites are printed in their own
         list so they stay visible in every run;
      6. its operand is not a FIXED IMAGE ADDRESS - `base - kImageBase +
         0xB43DD0`, `d + 0xB43DD8`, a bare `0x00B43CEC`: a known .data global
         of the game is not a guess (5+ hex digits; small struct offsets such
         as `raw + 0xf0` are still derefs). Reported as info.

    `- base + kImageBase` REBASE arithmetic is reported as INFO only: it marks
    where a probe turns a pointer into an image VA for a log line, but the
    subtraction itself cannot fault. `--info` lists those sites and the
    out-of-scope shapes for triage.

    A site that is only null-checked is NOT guarded: `if (linked)` proved the
    field non-zero and the process still died (SpGetterLog, 2026-08-18).

SELF-TEST (--selftest)
    Proves, on inline synthetic snippets: a probe-scope function with all three
    shapes goes RED; the same body under __try is GREEN; the same body in a
    non-probe function is GREEN (counted out of scope); a function that calls
    `_ReturnAddress()` is in scope by that alone; `// deref-ok:` moves a site
    to the waived list; ProbeSafe-validated identifiers are not flagged;
    fixed image addresses are info; rebase is info, not red; comments and strings never fire; a whole-body
    __try helper is derived; and a guard does not leak past its closing
    brace. A gate that has never rejected anything is not evidence.

USAGE
    python _tests\Test-ProbeDerefGuards.py            # scan src\CodePatches.cpp + src\UiSpike.cpp
    python _tests\Test-ProbeDerefGuards.py --selftest
    python _tests\Test-ProbeDerefGuards.py --info     # also list rebase + out-of-scope sites
    python _tests\Test-ProbeDerefGuards.py --allow SafeVt --file src\Other.cpp

Exit 0 = no RED site (or self-test passed). Exit 1 = at least one RED site,
printed as `file:line: [shape] Function: <snippet>` (or self-test failed).
Exit 2 = a source file is missing.
"""

import argparse
import bisect
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_FILES = [
    os.path.join("src", "CodePatches.cpp"),
    os.path.join("src", "UiSpike.cpp"),
]

PROBE_NAME = re.compile(r"(Log|Detour|Thunk|Probe|Cap|Census|Scan)|^Sp")
RETADDR = re.compile(r"\b_ReturnAddress\s*\(")
WAIVER = re.compile(r"//\s*deref-ok:\s*(.*)")

# ---------------------------------------------------------------------------
# lexical helpers
# ---------------------------------------------------------------------------

def mask_source(text):
    """Blank comments and string/char literals with spaces, keeping every
    newline and the byte length, so offsets and line numbers survive."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif c == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if text[k] != "\n":
                    out[k] = " "
            i = j
        elif c == '"' or c == "'":
            q = c
            j = i + 1
            while j < n and text[j] != q and text[j] != "\n":
                if text[j] == "\\":
                    j += 1
                j += 1
            for k in range(i + 1, min(j, n)):
                out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


def match_brace(masked, open_pos, open_ch="{", close_ch="}"):
    depth = 0
    j = open_pos
    n = len(masked)
    while j < n:
        ch = masked[j]
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return n - 1


def try_spans(masked):
    """[(start, end)] covering `__try { ... }` (keyword through closing brace)."""
    spans = []
    for m in re.finditer(r"\b__try\b", masked):
        ob = masked.find("{", m.end())
        if ob == -1 or masked[m.end():ob].strip():
            continue
        spans.append((m.start(), match_brace(masked, ob)))
    return spans


KEYWORDS = {"if", "while", "for", "switch", "catch", "return", "sizeof", "__except",
            "__declspec", "alignas", "decltype", "defined", "else", "do", "static_assert"}

RX_FN_HEAD = re.compile(r"\b([A-Za-z_]\w*)\s*\(")


def functions(masked):
    """[(name, body_open, body_close)] for every `Name(...) {` definition, in
    order. Bodies do not nest (lambdas inside a body are not registered)."""
    fns = []
    skip_to = -1
    for m in RX_FN_HEAD.finditer(masked):
        if m.start() < skip_to:
            continue
        name = m.group(1)
        if name in KEYWORDS:
            continue
        close = match_brace(masked, m.end() - 1, "(", ")")
        mm = re.match(r"\s*(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?\{", masked[close + 1:close + 64])
        if not mm:
            continue
        body_open = close + 1 + mm.end() - 1
        body_close = match_brace(masked, body_open)
        fns.append((name, body_open, body_close))
        skip_to = body_close
    return fns


def whole_body_try_helpers(masked, spans):
    """Functions whose entire body is one __try/__except: name -> (start, end)
    of the body. Derived, not declared."""
    helpers = {}
    for ts, te in spans:
        pre = masked[:ts].rstrip()
        if not pre.endswith("{"):
            continue
        body_open = len(pre) - 1
        rest = masked[te + 1:]
        m = re.match(r"\s*__except\s*\(", rest)
        if not m:
            continue
        paren_open = te + 1 + m.end() - 1
        paren_close = match_brace(masked, paren_open, "(", ")")
        hb = masked.find("{", paren_close)
        if hb == -1 or masked[paren_close + 1:hb].strip():
            continue
        he = match_brace(masked, hb)
        tail = masked[he + 1:]
        if not (re.match(r"\s*}", tail) or re.match(r"\s*return\b[^;]*;\s*}", tail)):
            continue
        sig = masked[:body_open].rstrip()
        sm = re.search(r"(\w+)\s*\([^(){};]*\)\s*(?:const\s*)?$", sig)
        if not sm or sm.group(1) in KEYWORDS:
            continue
        helpers[sm.group(1)] = (body_open, match_brace(masked, body_open))
    return helpers


def function_bodies_named(masked, names):
    """Body spans of every definition of the named functions (for --allow)."""
    spans = []
    for name in names:
        for m in re.finditer(r"\b%s\s*\([^(){};]*\)\s*(?:const\s*)?\{" % re.escape(name), masked):
            ob = m.end() - 1
            spans.append((ob, match_brace(masked, ob)))
    return spans


# ---------------------------------------------------------------------------
# the shapes
# ---------------------------------------------------------------------------

RX_REBASE = re.compile(r"-\s*base\s*\+\s*kImageBase\b")
RX_VPTR = re.compile(
    r"\*\s*reinterpret_cast\s*<\s*(?:const\s+)?"
    r"(?:void\s*\*\s*\*(?:\s*\*)?|uintptr_t\s*\*)\s*>\s*\(")
VT_IDENT = r"(pv|\w*[vV]t\d*)"
RX_SLOT_CALL = re.compile(
    r"reinterpret_cast\s*<\s*\w+\s*>\s*\(\s*" + VT_IDENT + r"\s*\[[^\]]*\]\s*\)\s*\(")
RX_SLOT_STORE = re.compile(
    r"\b(\w+)\s*=\s*reinterpret_cast\s*<\s*\w+\s*>\s*\(\s*" + VT_IDENT + r"\s*\[[^\]]*\]\s*\)\s*;")
RX_PEEK = re.compile(r"\b(\w+)\s*\[\s*-\s*\d+\s*\]\s*==\s*0x[0-9A-Fa-f]+")
SLOT_STORE_WINDOW = 12   # lines after `fn = reinterpret_cast<Fn>(vt[n]);` to look for `fn(`

# ProbeSafe validation: identifiers whose VALUE came out of a guarded helper
RX_VALID_ASSIGN = re.compile(r"\b(\w+)\s*=\s*(?:ProbeSafe::)?(?:SafeVt|SafeSlot)\s*\(")
RX_VALID_READPTR = re.compile(r"(?:ProbeSafe::)?ReadPtr\s*\((?:[^;()]|\([^()]*\))*?&\s*(\w+)\s*[,)]")
RX_VALID_READBYTES = re.compile(r"(?:ProbeSafe::)?ReadBytes\s*\((?:[^,()]|\([^()]*\))*,\s*(\w+)\s*,")


def is_write_through(masked, cast_open_paren):
    """True when `*reinterpret_cast<..>( ... )` is the LEFT side of `=`."""
    close = match_brace(masked, cast_open_paren, "(", ")")
    rest = masked[close + 1:close + 4].lstrip()
    return rest.startswith("=") and not rest.startswith("==")


def operand(masked, cast_open_paren):
    """The text inside `*reinterpret_cast<..>( ... )`."""
    close = match_brace(masked, cast_open_paren, "(", ")")
    return masked[cast_open_paren + 1:close].strip()


def base_ident(masked, cast_open_paren):
    """The bare identifier inside `*reinterpret_cast<..>( IDENT )`, else None."""
    inner = operand(masked, cast_open_paren)
    return inner if re.fullmatch(r"\w+", inner) else None


RX_FIXED = (re.compile(r"kImageBase\s*\+\s*0x[0-9A-Fa-f]{5,}"),
            re.compile(r"^\w+\s*\+\s*0x[0-9A-Fa-f]{5,}$"),
            re.compile(r"^(?:reinterpret_cast\s*<[^>]*>\s*\()?\s*0x[0-9A-Fa-f]{5,}\s*\)?$"))


def is_fixed_address(inner):
    """True for a read of a known game global by absolute image address."""
    return any(rx.search(inner) for rx in RX_FIXED)


def scan_text(label, text, allow=()):
    """Return (red, waived, info). A site is (line, shape, fn, snippet[, reason])."""
    masked = mask_source(text)
    lines = text.split("\n")
    mlines = masked.split("\n")
    line_starts = [0]
    for ln in mlines[:-1]:
        line_starts.append(line_starts[-1] + len(ln) + 1)
    spans = try_spans(masked)
    helpers = whole_body_try_helpers(masked, spans)
    guarded = list(spans) + list(helpers.values()) + function_bodies_named(masked, allow)
    fns = functions(masked)
    fn_opens = [f[1] for f in fns]

    def enclosing(pos):
        i = bisect.bisect_right(fn_opens, pos) - 1
        while i >= 0:
            name, o, c = fns[i]
            if o <= pos <= c:
                return fns[i]
            i -= 1
        return None

    fn_meta = {}
    for name, o, c in fns:
        body = masked[o:c + 1]
        in_scope = bool(PROBE_NAME.search(name)) or bool(RETADDR.search(body))
        validated = set(RX_VALID_ASSIGN.findall(body)) | set(RX_VALID_READPTR.findall(body)) \
            | set(RX_VALID_READBYTES.findall(body))
        fn_meta[o] = (in_scope, validated)

    def is_guarded(pos):
        return any(s <= pos <= e for s, e in guarded)

    # statement ids so a multi-line expression is reported once
    stmt_id = [0] * (len(masked) + 1)
    sid = 0
    for i, ch in enumerate(masked):
        stmt_id[i] = sid
        if ch in ";{}":
            sid += 1
    stmt_id[len(masked)] = sid

    hits = {}      # (stmt, shape) -> [lines]
    counts = {"rebase": 0, "vptr": 0, "vptr-write": 0, "slot": 0, "peek": 0,
              "guarded": 0, "out-of-scope": 0, "validated": 0, "fixed-address": 0, "no-fn": 0}
    info_sites = []

    def line_of(pos):
        return bisect.bisect_right(line_starts, pos)

    def add(pos, shape, ident=None, fixed=False):
        counts[shape] += 1
        line = line_of(pos)
        if shape == "rebase":
            info_sites.append((line, "rebase", (enclosing(pos) or ("?",))[0], lines[line - 1].strip()))
            return
        if fixed:
            counts["fixed-address"] += 1
            info_sites.append((line, "fixed-address " + shape, (enclosing(pos) or ("?",))[0], lines[line - 1].strip()))
            return
        if is_guarded(pos):
            counts["guarded"] += 1
            return
        fn = enclosing(pos)
        if fn is None:
            counts["no-fn"] += 1
            fname, in_scope, validated = "?", True, set()
        else:
            fname = fn[0]
            in_scope, validated = fn_meta[fn[1]]
        if ident and ident in validated:
            counts["validated"] += 1
            return
        if not in_scope:
            counts["out-of-scope"] += 1
            info_sites.append((line, "out-of-scope " + shape, fname, lines[line - 1].strip()))
            return
        hits.setdefault((stmt_id[pos], shape, fname), []).append(line)

    for m in RX_REBASE.finditer(masked):
        add(m.start(), "rebase")
    for m in RX_VPTR.finditer(masked):
        if is_write_through(masked, m.end() - 1):
            counts["vptr-write"] += 1
            continue
        add(m.start(), "vptr", base_ident(masked, m.end() - 1),
            fixed=is_fixed_address(operand(masked, m.end() - 1)))
    for m in RX_SLOT_CALL.finditer(masked):
        add(m.start(), "slot", m.group(1))
    for m in RX_SLOT_STORE.finditer(masked):
        name, vt = m.group(1), m.group(2)
        line = line_of(m.start())
        rx = re.compile(r"\b%s\s*\(" % re.escape(name))
        for k in range(line, min(line + SLOT_STORE_WINDOW, len(mlines))):
            cm = rx.search(mlines[k])
            if cm:
                add(line_starts[k] + cm.start(), "slot", vt)
                break
    for m in RX_PEEK.finditer(masked):
        add(m.start(), "peek", m.group(1))

    red, waived = [], []
    for (stmt, shape, fname), lns in hits.items():
        lns = sorted(set(lns))
        snippet = " ".join(lines[l - 1].strip() for l in lns)
        snippet = re.sub(r"\s+", " ", snippet)
        if len(snippet) > 110:
            snippet = snippet[:107] + "..."
        first = lns[0]
        reason = None
        for l in (first, first - 1):
            if 1 <= l <= len(lines):
                wm = WAIVER.search(lines[l - 1])
                if wm:
                    reason = wm.group(1).strip() or "(no reason given)"
                    break
        if reason is not None:
            waived.append((first, shape, fname, snippet, reason))
        else:
            red.append((first, shape, fname, snippet))
    red.sort()
    waived.sort()
    info = dict(label=label, try_spans=len(spans), helpers=sorted(helpers), counts=counts,
                functions=len(fns), probe_functions=sum(1 for o in fn_meta if fn_meta[o][0]),
                info_sites=sorted(info_sites))
    return red, waived, info


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

PROBE_BODY = """
        const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        void** vt = *reinterpret_cast<void***>(obj);
        const uint32_t vtVa = static_cast<uint32_t>(
            reinterpret_cast<uintptr_t>(vt) - base + kImageBase);
        const uint32_t type = reinterpret_cast<ObjGetTypeFn>(vt[0x1C / 4])(obj);
        SlotFn fn = reinterpret_cast<SlotFn>(vt[7]);
        fn(obj, 1);
        const uint8_t* c = reinterpret_cast<const uint8_t*>(self);
        const bool isRet = (c[-5] == 0xE8) || (c[-2] == 0xFF);
        Log("%u %u %d", vtVa, type, isRet);
"""

RED_BODY = "    void __stdcall SpFooLog(void* self, void* obj)\n    {\n" + PROBE_BODY + "    }\n"

GREEN_TRY_BODY = ("    void __stdcall SpFooLog(void* self, void* obj)\n    {\n        __try\n        {\n"
                  + PROBE_BODY +
                  "        }\n        __except (EXCEPTION_EXECUTE_HANDLER)\n        {\n            Log(\"<fault>\");\n        }\n    }\n")

GREEN_SCOPE_BODY = "    void ApplyLayout(void* self, void* obj)\n    {\n" + PROBE_BODY + "    }\n"

RED_RETADDR_BODY = """
    void __fastcall CheckCaller(void* self, void* edx)
    {
        const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        const uint32_t ret = static_cast<uint32_t>(
            reinterpret_cast<uintptr_t>(_ReturnAddress()) - base + kImageBase);
        const uintptr_t vt = *reinterpret_cast<uintptr_t*>(self);
        Log("%u %u", ret, vt);
    }
"""

WAIVED_BODY = """
    void __stdcall SpBarLog(void* self, void* win)
    {
        // deref-ok: win is the live window EnumChildren just handed us
        void** vt = *reinterpret_cast<void***>(win);
        const uintptr_t v2 = *reinterpret_cast<uintptr_t*>(self);   // deref-ok: self is the hooked this
        Log("%p %u", vt, v2);
    }
"""

GREEN_PROBESAFE_BODY = """
    void __stdcall SpBazLog(void* self, void* obj)
    {
        void** vt = ProbeSafe::SafeVt(obj);
        const uintptr_t getType = ProbeSafe::SafeSlot(vt, 7);
        if (getType) { reinterpret_cast<ObjGetTypeFn>(getType)(obj); }
        reinterpret_cast<ObjRelFn>(vt[2])(obj);
        uintptr_t v = 0;
        if (!ProbeSafe::ReadPtr(self, &v)) { return; }
        void** dvt = *reinterpret_cast<void***>(v);
        uint8_t c[8] = {};
        if (!ProbeSafe::ReadBytes(reinterpret_cast<const uint8_t*>(v) - 7, c, 7)) { return; }
        Log("%p %p %d", vt, dvt, c[2]);
    }
"""

FIXED_BODY = """
    void InstallGlobalProbe()
    {
        const uintptr_t base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        const uintptr_t d = base - kImageBase;
        void* svc = *reinterpret_cast<void**>(base - kImageBase + 0xB43DD0);
        void* vu = *reinterpret_cast<void**>(d + 0xB43DD8);
        void* terrain = *reinterpret_cast<void**>(0x00B43CEC);
        void** vt = *reinterpret_cast<void***>(svc);
        Log("%p %p %p %p", svc, vu, terrain, vt);
    }
"""

NOISE_BODY = """
    // void** vt = *reinterpret_cast<void***>(obj); reinterpret_cast<Fn>(vt[1])(obj);
    /* x - base + kImageBase   c[-5] == 0xE8 */
    const char* kDoc = "*reinterpret_cast<void***>(obj) - base + kImageBase c[-5] == 0xE8";
    void SpSwapDetour(void* w) { *reinterpret_cast<void***>(w) = gVtCopy; }
    uint32_t SafeVt(const void* p)
    {
        __try
        {
            void** vt = *reinterpret_cast<void***>(const_cast<void*>(p));
            return reinterpret_cast<ObjGetTypeFn>(vt[7])(const_cast<void*>(p));
        }
        __except (EXCEPTION_EXECUTE_HANDLER)
        {
            return 0xFFFFFFFFu;
        }
    }
"""


def selftest():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    red, waived, info = scan_text("red", RED_BODY)
    shapes = sorted(set(s for _, s, _, _ in red))
    check(shapes == ["peek", "slot", "vptr"], "RED: expected peek/slot/vptr, got %s (%s)" % (shapes, red))
    check(sum(1 for r in red if r[1] == "slot") == 2, "RED: expected 2 slot calls (direct + stored), got %s" % red)
    check(all(r[2] == "SpFooLog" for r in red), "RED: enclosing function should be SpFooLog: %s" % red)
    check(info["counts"]["rebase"] == 1 and not any(s == "rebase" for _, s, _, _ in red),
          "RED: rebase must be info only, counts=%s red=%s" % (info["counts"], red))

    red, waived, info = scan_text("green-try", GREEN_TRY_BODY)
    check(not red and not waived, "GREEN-TRY: expected nothing, got red=%s waived=%s" % (red, waived))
    check(info["try_spans"] == 1 and info["counts"]["guarded"] >= 3,
          "GREEN-TRY: shapes must still be COUNTED as guarded: %s" % info["counts"])

    red, waived, info = scan_text("green-scope", GREEN_SCOPE_BODY)
    check(not red, "GREEN-SCOPE: non-probe function must not be red, got %s" % red)
    check(info["counts"]["out-of-scope"] >= 3, "GREEN-SCOPE: shapes should be counted out of scope: %s" % info["counts"])

    red, waived, info = scan_text("red-retaddr", RED_RETADDR_BODY)
    check([r[1] for r in red] == ["vptr"] and red[0][2] == "CheckCaller",
          "RED-RETADDR: _ReturnAddress() must put CheckCaller in scope, got %s" % red)

    red, waived, info = scan_text("waived", WAIVED_BODY)
    check(not red and len(waived) == 2, "WAIVED: expected 0 red / 2 waived, got red=%s waived=%s" % (red, waived))
    check(waived and "EnumChildren" in waived[0][4], "WAIVED: reason text must be carried: %s" % waived)

    red, waived, info = scan_text("green-probesafe", GREEN_PROBESAFE_BODY)
    check(not red, "GREEN-PROBESAFE: ProbeSafe-validated identifiers must not be red, got %s" % red)
    check(info["counts"]["validated"] >= 2, "GREEN-PROBESAFE: expected validated skips, got %s" % info["counts"])

    red, waived, info = scan_text("fixed", FIXED_BODY)
    check(len(red) == 1 and red[0][1] == "vptr" and "svc" in red[0][3],
          "FIXED: only the deref of the fetched pointer may be red, got %s" % red)
    check(info["counts"]["fixed-address"] == 3, "FIXED: expected 3 fixed-address reads as info, got %s" % info["counts"])

    red, waived, info = scan_text("noise", NOISE_BODY)
    check(not red and not waived, "NOISE: comments/strings/writes/whole-body helper must not fire, got %s %s" % (red, waived))
    check(info["helpers"] == ["SafeVt"], "NOISE: SafeVt should be derived as a whole-body-__try helper, got %s" % info["helpers"])
    check(info["counts"]["vptr-write"] == 1, "NOISE: exactly one vptr WRITE expected, got %s" % info["counts"])

    leak = GREEN_TRY_BODY + "\n    void SpTailLog(void* o) { void** vt = *reinterpret_cast<void***>(o); }\n"
    red, _, _ = scan_text("leak", leak)
    check([r[1] for r in red] == ["vptr"] and red[0][2] == "SpTailLog",
          "LEAK: the site after the __try must be RED in SpTailLog, got %s" % red)

    total = 17
    for f in failures:
        print("SELFTEST FAIL: " + f)
    print("selftest: %d/%d checks passed" % (total - len(failures), total))
    return 0 if not failures else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--selftest", action="store_true", help="prove the gate can go red and green")
    ap.add_argument("--repo", default=REPO, help="repo root (default: parent of _tests)")
    ap.add_argument("--file", action="append", help="source file(s) to scan, relative to --repo (default: the two probe files)")
    ap.add_argument("--allow", action="append", default=[], help="helper whose body is treated as guarded (e.g. SafeVt)")
    ap.add_argument("--info", action="store_true", help="also list rebase sites and out-of-scope shapes")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    files = args.file or DEFAULT_FILES
    total_red = 0
    for rel in files:
        path = os.path.join(args.repo, rel)
        if not os.path.isfile(path):
            print("MISSING: %s" % path)
            return 2
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        red, waived, info = scan_text(rel, text, args.allow)
        for line, shape, fname, snippet in red:
            print("%s:%d: [%s] %s: %s" % (rel, line, shape, fname, snippet))
        if waived:
            print("WAIVED (deref-ok) in %s:" % rel)
            for line, shape, fname, snippet, reason in waived:
                print("  %s:%d: [%s] %s: %s  -- %s" % (rel, line, shape, fname, snippet, reason))
        if args.info and info["info_sites"]:
            print("INFO in %s:" % rel)
            for line, kind, fname, snippet in info["info_sites"]:
                print("  %s:%d: [%s] %s: %s" % (rel, line, kind, fname, snippet[:100]))
        total_red += len(red)
        c = info["counts"]
        print("-- %s: %d RED, %d waived; probe-scope functions %d of %d; __try spans %d; "
              "whole-body-__try helpers %s; shapes seen vptr=%d slot=%d peek=%d -> guarded %d, "
              "ProbeSafe-validated %d, out of scope %d, fixed image address %d, no enclosing fn %d; "
              "rebase (info only) %d; vptr writes (not gated) %d"
              % (rel, len(red), len(waived), info["probe_functions"], info["functions"],
                 info["try_spans"], info["helpers"] or "[]",
                 c["vptr"], c["slot"], c["peek"], c["guarded"], c["validated"], c["out-of-scope"],
                 c["fixed-address"], c["no-fn"], c["rebase"], c["vptr-write"]))
    print("Test-ProbeDerefGuards: %d unguarded speculative read(s) in probe/detour scope -> %s"
          % (total_red, "RED" if total_red else "GREEN"))
    return 1 if total_red else 0


if __name__ == "__main__":
    sys.exit(main())
