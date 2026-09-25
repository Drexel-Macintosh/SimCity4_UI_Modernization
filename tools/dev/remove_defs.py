"""remove_defs.py - delete whole C++ definitions (functions, structs, header
declarations) by NAME, with the comment block directly above them.

Written for the 2026-09-25 audit's dead-code pass (research/AUDIT-2026-09-25-
EFFICIENCY.md B1/B3). Deleting by name + brace matching instead of by line
number keeps working after unrelated edits shift the file.

    python tools/dev/remove_defs.py [--apply] FILE:KIND:NAME [...]

KIND: func   a function definition (return type, name, params, body)
      struct a struct/class definition, through its closing '};'
      decl   a declaration ending in ';' (header prototypes)

Without --apply it only prints what it would remove. Every NAME must match
exactly one definition of that KIND in FILE, or nothing is written. Braces
inside strings, chars and comments are ignored. The compiler is the real
gate: build after applying, and a link error names anything still in use.
"""
import re
import sys

KEYWORDS = {"return", "else", "case", "new", "delete", "throw", "goto", "sizeof"}


def code_mask(text):
    """Per character: True when it is code (not in a comment/string/char)."""
    mask = [True] * len(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                mask[k] = False
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                mask[k] = False
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            for k in range(i, min(j + 1, n)):
                mask[k] = False
            i = j + 1
        else:
            i += 1
    return mask


def find_region(text, mask, kind, name):
    hits = []
    if kind == "struct":
        pat = re.compile(r"^[ \t]*(?:struct|class)[ \t]+%s\b" % re.escape(name), re.M)
    else:
        # single-line signatures only: the return type may not span lines
        pat = re.compile(r"^[ \t]*([\w:<>,\*& \t]+?)[ \t\*&]+(?:\w+::)?%s[ \t]*\(" % re.escape(name), re.M)
    for m in pat.finditer(text):
        if not mask[m.start() + len(m.group(0)) - 1]:
            continue
        if kind != "struct":
            words = m.group(1).split()
            if not words or words[0] in KEYWORDS or "=" in m.group(1):
                continue
        # scan forward (code only) to the first '{' or ';' at paren depth 0
        i, depth, end_tok = m.end() - 1 if kind != "struct" else m.end(), 0, None
        while i < len(text):
            if mask[i]:
                ch = text[i]
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                elif depth == 0 and ch in "{;":
                    end_tok = (ch, i)
                    break
            i += 1
        if end_tok is None:
            continue
        ch, pos = end_tok
        if kind == "decl":
            if ch != ";":
                continue
            stop = pos + 1
        else:
            if ch != "{":
                continue
            braces, j = 0, pos
            while j < len(text):
                if mask[j]:
                    if text[j] == "{":
                        braces += 1
                    elif text[j] == "}":
                        braces -= 1
                        if braces == 0:
                            break
                j += 1
            stop = j + 1
            if kind == "struct":
                semi = text.find(";", stop)
                if semi >= 0 and text[stop:semi].strip() == "":
                    stop = semi + 1
        hits.append((m.start(), stop))
    return hits


def expand(text, start, stop):
    """Grow [start, stop) to whole lines, the comment block directly above,
    and one trailing blank line."""
    s = text.rfind("\n", 0, start) + 1
    e = text.find("\n", stop)
    e = len(text) if e < 0 else e + 1
    while s > 0:
        prev_s = text.rfind("\n", 0, s - 1) + 1
        line = text[prev_s:s].strip()
        if line.startswith("//"):
            s = prev_s
        else:
            break
    nxt = text.find("\n", e)
    if nxt >= 0 and text[e:nxt].strip() == "":
        e = nxt + 1
    return s, e


def main(argv):
    apply = "--apply" in argv
    specs = [a for a in argv if a != "--apply"]
    by_file = {}
    for spec in specs:
        path, kind, name = spec.rsplit(":", 2)
        by_file.setdefault(path, []).append((kind, name))
    ok = True
    plans = {}
    for path, items in by_file.items():
        with open(path, "rb") as fh:
            raw = fh.read()
        text = raw.decode("utf-8")
        mask = code_mask(text)
        regions = []
        for kind, name in items:
            hits = find_region(text, mask, kind, name)
            if len(hits) != 1:
                print("REFUSED %s %s:%s - %d matches (need exactly 1)" % (path, kind, name, len(hits)))
                ok = False
                continue
            s, e = expand(text, *hits[0])
            first = text.count("\n", 0, s) + 1
            last = text.count("\n", 0, e)
            print("%-8s %-28s %s:%d-%d (%d lines)  %r"
                  % (kind, name, path.split("\\")[-1].split("/")[-1], first, last,
                     last - first + 1, text[hits[0][0]:hits[0][0] + 60].strip()))
            regions.append((s, e))
        plans[path] = (text, regions)
    if not ok:
        print("NOTHING WRITTEN.")
        return 1
    if not apply:
        print("dry run - pass --apply to write.")
        return 0
    for path, (text, regions) in plans.items():
        for s, e in sorted(regions, reverse=True):
            text = text[:s] + text[e:]
        text = re.sub(r"\nnamespace[ \t]*\r?\n?[ \t]*\{\s*\}[ \t]*\r?\n", "\n", text)
        with open(path, "wb") as fh:
            fh.write(text.encode("utf-8"))
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
