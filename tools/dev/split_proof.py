"""split_proof.py - did a translation-unit split only MOVE code? Compares the
objects of the one-file build against the objects of the split build.

    python tools/dev/split_proof.py OLD.obj -- NEW1.obj NEW2.obj

Build both sides UNOPTIMIZED and with every global in its own section, e.g.
    cl /c /Od /Gw ...        (or clang-cl --target=i686-pc-windows-msvc /c /Od /Gw ...)
Unoptimized, each function's machine code comes from its own source alone:
optimized code also reflects where its callees live (inlining, calling
conventions, and a whole-program build merges the modules in a new order),
so an optimized comparison differs even for a pure move. /Gw gives every
global its own section, so no global's bytes run into its neighbour's.

It reads the COFF objects directly (i386) and, for every symbol that owns bytes
- functions in code sections, variables in data sections - builds
    (size, bytes with every relocated field blanked, [(offset, type, target)])
where target is the relocation's symbol, or for a section-relative relocation
(a static in .rdata/.data) the symbol that owns that offset plus the distance
into it; an unnamed constant in a section of its own is named by its bytes.
Names are normalized for what a split changes: the anonymous-namespace tag
?A0x...@ and UiSpikeInternal@ both become NS@, and mangled back-references are
compared as a class (UiSpikeInternal takes a slot in the back-reference table,
the anonymous namespace does not). Compiler-numbered ___unnamed_N labels are
named by what they hold.

The two sides must hold the same symbols with identical records; a symbol two
NEW objects both define (a COMDAT inline) must be identical in both. Exit 0 =
a pure move; 1 = something differs, and the report says what.
Used for the audit B11 splits (2026-09-25).
"""
import re, struct, sys, collections

NORM = [(re.compile(r"\?A0x[0-9a-fA-F]{1,8}@"), "NS@"), (re.compile(r"UiSpikeInternal@"), "NS@"),
        (re.compile(r"(?<=[A-Z@])[0-9](?=@)"), "#"),
        # A struct named inside its own namespace: the anonymous namespace is
        # spelled out (U1?A0x...@@), UiSpikeInternal is a back-reference (U12@).
        (re.compile(r"(?<=[A-Z])([0-9])NS@@"), r"\1#@"), (re.compile(r"(?<=[A-Z])([0-9])[0-9]@"), r"\1#@"),
        (re.compile(r"@NS@@"), "@#@")]


def norm(n):
    for rx, r in NORM:
        n = rx.sub(r, n)
    return n


class Obj:
    def __init__(self, path):
        d = open(path, "rb").read()
        self.path = path
        mach, nsec, _, psym, nsym, optsz, _ = struct.unpack_from("<HHIIIHH", d, 0)
        assert mach == 0x14C, "not i386"
        strtab = psym + nsym * 18
        def sname(raw):
            if raw[:4] == b"\0\0\0\0":
                off = struct.unpack_from("<I", raw, 4)[0]
                e = d.index(b"\0", strtab + off)
                return d[strtab + off:e].decode("latin-1")
            return raw.rstrip(b"\0").decode("latin-1")
        self.secs = []
        for i in range(nsec):
            o = 20 + optsz + 40 * i
            name = d[o:o + 8]
            vsz, va, rsz, praw, prel, pln, nrel, nln, ch = struct.unpack_from("<IIIIIIHHI", d, o + 8)
            if name[:1] == b"/":
                off = int(name[1:].rstrip(b"\0"))
                e = d.index(b"\0", strtab + off)
                name = d[strtab + off:e]
            name = name.rstrip(b"\0").decode("latin-1")
            raw = d[praw:praw + rsz] if praw else b"\0" * rsz
            rels = [struct.unpack_from("<IIH", d, prel + 10 * k) for k in range(nrel)]
            self.secs.append({"name": name, "size": rsz, "raw": raw, "rels": rels, "ch": ch, "bss": praw == 0})
        self.syms = {}
        i = 0
        while i < nsym:
            o = psym + 18 * i
            raw = d[o:o + 8]
            val, secn, typ, scl, naux = struct.unpack_from("<IhHBB", d, o + 8)
            self.syms[i] = (sname(raw), val, secn, typ, scl, naux)
            i += 1 + naux
        # symbols that own bytes, per section, sorted by value
        self.owners = collections.defaultdict(list)
        for idx, (n, val, secn, typ, scl, naux) in self.syms.items():
            if secn <= 0 or scl not in (2, 3) or n.startswith("$") or n.startswith(".") \
                    or n.startswith("@feat") or n.startswith("__ehtable$") or n.startswith("___ehhandler$"):
                continue
            if scl == 3 and val == 0 and n == self.secs[secn - 1]["name"]:
                continue   # the section symbol itself
            self.owners[secn].append((val, n))
        for k in self.owners:
            self.owners[k].sort()

    def owner_at(self, secn, off):
        best = None
        for val, n in self.owners.get(secn, []):
            if val <= off:
                best = (val, n)
            else:
                break
        return best

    def target(self, symidx, addend):
        n, val, secn, typ, scl, naux = self.syms[symidx]
        if scl == 3 and val == 0 and secn > 0 and n == self.secs[secn - 1]["name"]:
            o = self.owner_at(secn, addend)
            if o is None:
                sec = self.secs[secn - 1]
                if not self.owners.get(secn):     # a section of its own (/Gw): name it by content
                    return "%s<%s>+0x%x" % (n, sec["raw"].hex() if not sec["bss"] else "bss%d" % sec["size"], addend)
                return "%s+0x%x" % (n, addend)
            return "%s+0x%x" % (norm(o[1]), addend - o[0])
        return norm(n)

    def records(self):
        out = {}
        for secn, lst in self.owners.items():
            s = self.secs[secn - 1]
            for j, (val, n) in enumerate(lst):
                end = lst[j + 1][0] if j + 1 < len(lst) else s["size"]
                if end == val and j + 1 < len(lst):
                    continue          # an alias at the same offset: the next one owns the bytes
                body = bytearray(s["raw"][val:end]) if not s["bss"] else None
                rels = []
                for (roff, ridx, rtyp) in s["rels"]:
                    if val <= roff < end:
                        addend = struct.unpack_from("<i", s["raw"], roff)[0] if not s["bss"] else 0
                        sn, sv, ssec, _, sscl, _ = self.syms[ridx]
                        is_section = sscl == 3 and sv == 0 and ssec > 0 and sn == self.secs[ssec - 1]["name"]
                        if rtyp == 0x14 and is_section:   # REL32 to a section: keep the raw addend
                            tgt = "%s(rel32 %d)" % (sn, addend)
                        elif rtyp == 0x14:                # REL32 to a symbol: the addend is -4 by construction
                            tgt = "%s(rel32 %d)" % (norm(sn), addend)
                        else:
                            tgt = self.target(ridx, addend)
                        rels.append((roff - val, rtyp, tgt))
                        if body is not None:
                            body[roff - val:roff - val + 4] = b"\0\0\0\0"
                kind = "code" if s["ch"] & 0x20 else ("bss" if s["bss"] else "data")
                key = norm(n)
                if key.startswith("___unnamed_") and rels:
                    # a compiler-numbered label (the RTTI slot ahead of a
                    # vftable): the number is per object, the content is not
                    key = "___unnamed<%s>" % rels[0][2]
                rec = (kind, end - val, bytes(body) if body is not None else None, tuple(rels))
                if key in out and out[key] != rec:
                    k = 2
                    while "%s #%d" % (key, k) in out:
                        k += 1
                    key = "%s #%d" % (key, k)
                out[key] = rec
        return out


def union(paths):
    u = {}
    for p in paths:
        for k, v in Obj(p).records().items():
            if k in u and u[k] != v:
                print("  DIFFERENT DUPLICATE across objects: %s" % k)
            u[k] = v
    return u


def main():
    args = sys.argv[1:]
    cut = args.index("--")
    old, new = union(args[:cut]), union(args[cut + 1:])
    only_old = sorted(set(old) - set(new))
    only_new = sorted(set(new) - set(old))
    # .bss has no bytes and COFF records no sizes: a size here is the distance
    # to the next symbol, i.e. includes padding. A one-byte type (bool, char)
    # whose "size" differs only moved in the layout.
    def bss_pad_only(k):
        a, b = old[k], new[k]
        return a[0] == b[0] == "bss" and a[3] == b[3] and re.search(r"[34](_N|D|E|C)A$", k.split(" #")[0])
    padded = sorted(k for k in set(old) & set(new) if old[k] != new[k] and bss_pad_only(k))
    changed = sorted(k for k in set(old) & set(new) if old[k] != new[k] and not bss_pad_only(k))
    if padded:
        print("  (%d one-byte .bss variable(s) sit at different padding: %s)" % (len(padded), ", ".join(p.split("@")[0] for p in padded)))
    kinds = collections.Counter(v[0] for v in old.values())
    print("symbols owning bytes: %d old (%s), %d new; only-old %d, only-new %d, changed %d, identical %d"
          % (len(old), ", ".join("%s %d" % kv for kv in sorted(kinds.items())), len(new),
             len(only_old), len(only_new), len(changed), len(set(old) & set(new)) - len(changed)))
    for tag, lst in (("ONLY-OLD", only_old), ("ONLY-NEW", only_new)):
        for k in lst[:40]:
            print("  %s %s" % (tag, k[:160]))
    for k in changed[:40]:
        a, b = old[k], new[k]
        why = []
        if a[0] != b[0]: why.append("kind %s->%s" % (a[0], b[0]))
        if a[1] != b[1]: why.append("size %d->%d" % (a[1], b[1]))
        if a[2] != b[2]: why.append("bytes")
        if a[3] != b[3]:
            sa, sb = set(a[3]), set(b[3])
            why.append("relocs -%s +%s" % (sorted(sa - sb)[:3], sorted(sb - sa)[:3]))
        print("  CHANGED %s: %s" % (k[:120], "; ".join(why)[:600]))
    return 1 if (only_old or only_new or changed) else 0


if __name__ == "__main__":
    sys.exit(main())
