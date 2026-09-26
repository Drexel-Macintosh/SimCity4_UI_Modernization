"""check_call_sites.py - can any IniCache read in src/ reach a query class
where IniCache differs from the real Windows profile API?

The parity harness (inicache_parity.cpp) fuzzes pathological queries. On real
Windows (2026-09-25) IniCache agreed with GetPrivateProfileString everywhere
EXCEPT five query classes: an empty section name, a key beginning with ';',
a tab inside a section/key name, a default with trailing blanks, and a
default wrapped in quotes. Wine agrees with IniCache on those, which is why
the harness passed in the Linux container. This scan proves the DLL never
issues such a query, by reading every IniCache::Read* call's literal
arguments. A call whose section/key/default is not a string literal is
reported, so it can be checked by hand.

Exit 0 = every call site is outside the five classes; 1 = a site is inside
one (or unverifiable); the report names it.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC = os.path.join(ROOT, "src")
CALL = re.compile(r"IniCache::(Read\w+)\s*\(")
LIT = re.compile(r'^\s*L?"((?:[^"\\]|\\.)*)"\s*$')


def split_args(text, start):
    """Top-level comma split of the argument list starting after '('."""
    depth, i, cur, args = 1, start, [], []
    while i < len(text) and depth:
        ch = text[i]
        if ch == '"':
            j = i + 1
            while j < len(text) and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            cur.append(text[i:j + 1])
            i = j + 1
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                break
        if ch == "," and depth == 1:
            args.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    args.append("".join(cur))
    return [a.strip() for a in args]


def lit(arg):
    m = LIT.match(arg)
    return None if m is None else m.group(1)


def main():
    sites = bad = unverified = 0
    for name in sorted(os.listdir(SRC)):
        if not name.endswith((".cpp", ".h")) or name.startswith("IniCache"):
            continue
        text = open(os.path.join(SRC, name), encoding="utf-8-sig", errors="replace").read()
        for m in CALL.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            args = split_args(text, m.end())
            if len(args) < 2:
                continue
            sites += 1
            sec, key = lit(args[0]), lit(args[1])
            default = lit(args[2]) if (m.group(1).startswith("ReadString") and len(args) > 2) else ""
            where = "%s:%d %s" % (name, line, m.group(1))
            if sec is None or key is None or default is None:
                unverified += 1
                print("CHECK BY HAND  %s  args=%s" % (where, args[:3]))
                continue
            why = []
            if sec == "":
                why.append("empty section")
            if key.startswith(";"):
                why.append("key starts with ';'")
            if "\\t" in sec + key or "\t" in sec + key:
                why.append("tab in a name")
            if default != default.rstrip(" \\t") or default.endswith("\\t"):
                why.append("default ends in blanks")
            if len(default) >= 2 and default[0] == default[-1] and default[0] in "\"'" or default.startswith('\\"'):
                why.append("quoted default")
            if why:
                bad += 1
                print("DIFFERS FROM WINDOWS  %s  [%s] %s def=%r: %s" % (where, sec, key, default, ", ".join(why)))
    print("%d IniCache call site(s): %d in a differing class, %d to check by hand"
          % (sites, bad, unverified))
    if sites == 0:
        print("FAIL: found no call sites - the scan is looking in the wrong place")
        return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
