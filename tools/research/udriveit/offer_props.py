#!/usr/bin/env python3
r"""Find every exemplar in every DISCOVERED .dat that carries the U-Drive-It
offer properties reached by the binder at 0x496950.  READ-ONLY.

  0xEA123CEF  offer LOOKUP TABLE  (uint32 vector; pairs key->offerId, or a
              single default) -- read at 0x49697A via helper 0x5FF510
  0x2977AA47  the key looked up in that table -- read at 0x4969C9
  0x4A70D491  a VETO property: if the exemplar HAS it, 0x496950 bails (0x4969AC)

The two offer-family ids the caller 0x4902E0 tests for are
0xEA123BE1 (@0x490337) and 0xAA123BF9 (@0x49033F).

POSITIVE CONTROL: the same walk must also find the well-known marker exemplars
(type 0x6534284A group 0xC977C536) -- we print the total exemplar count so a
zero-hit result can be told apart from a broken walk.

    python offer_props.py
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))

from census_markers import (dbpf_index, read_entry, maybe_decompress,   # noqa
                            parse_exemplar, discover_dbpf)
from sc4paths import plugins_dir, game_dir                              # noqa

T_EXEMPLAR = 0x6534284A
T_COHORT = 0x05342861

P_TABLE = 0xEA123CEF
P_KEY = 0x2977AA47
P_VETO = 0x4A70D491
OFFER_IDS = {0xEA123BE1: "offer family A (0x490337)",
             0xAA123BF9: "offer family B (0x49033F)"}

NAME_PROP = 0x00000020


def as_ints(v):
    """parse_exemplar returns (typename, [values]); values may be bytes."""
    if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str):
        v = v[1]
    out = []
    if isinstance(v, (list, tuple)):
        for x in v:
            if isinstance(x, bool):
                out.append(int(x))
            elif isinstance(x, int):
                out.append(x)
            elif isinstance(x, float):
                out.append(int(x))
    elif isinstance(v, int):
        out.append(v)
    return out


def as_name(v):
    if isinstance(v, tuple) and len(v) == 2:
        v = v[1]
    if isinstance(v, (list, tuple)) and v:
        v = v[0]
    if isinstance(v, bytes):
        return v.decode("latin1", "replace")
    return str(v)


def main():
    roots = [game_dir()]
    p = plugins_dir(require=False)
    if p:
        roots.append(p)
    dats = []
    for r in roots:
        dats.extend(discover_dbpf(r))
    print(f"archives discovered: {len(dats)}")
    for d in dats:
        print(f"   {d}")

    n_ex = 0
    hits_table = []
    hits_key = defaultdict(list)
    hits_veto = []
    offer_carriers = []

    for path in dats:
        for (t, g, i, off, sz) in dbpf_index(path):
            if t not in (T_EXEMPLAR, T_COHORT):
                continue
            n_ex += 1
            try:
                payload, _ = maybe_decompress(read_entry(path, off, sz))
                _parent, props, _o = parse_exemplar(payload)
            except Exception:
                continue
            if not props:
                continue
            name = as_name(props[NAME_PROP]) if NAME_PROP in props else ""
            base = os.path.basename(path)
            if P_TABLE in props:
                vals = as_ints(props[P_TABLE])
                hits_table.append((t, g, i, base, name, vals))
                for v in vals:
                    if v in OFFER_IDS:
                        offer_carriers.append((t, g, i, base, name, vals))
                        break
            if P_KEY in props:
                hits_key[tuple(as_ints(props[P_KEY]))].append(
                    (t, g, i, base, name))
            if P_VETO in props:
                hits_veto.append((t, g, i, base, name))

    print(f"\nexemplars/cohorts walked: {n_ex}")

    print(f"\n== carriers of 0xEA123CEF (the offer LOOKUP TABLE): "
          f"{len(hits_table)} ==")
    for t, g, i, base, name, vals in hits_table:
        vs = ", ".join(f"0x{v:08X}" for v in vals)
        print(f"  {{T=0x{t:08X}, G=0x{g:08X}, I=0x{i:08X}}} [{base}] "
              f"{name!r}\n        table = [{vs}]")

    print(f"\n== of those, tables naming an OFFER id: {len(offer_carriers)} ==")
    for t, g, i, base, name, vals in offer_carriers:
        print(f"  {{T=0x{t:08X}, G=0x{g:08X}, I=0x{i:08X}}} [{base}] {name!r}")

    print(f"\n== carriers of 0x2977AA47 (the lookup KEY): "
          f"{sum(len(v) for v in hits_key.values())} exemplars, "
          f"{len(hits_key)} distinct values ==")
    for val, lst in sorted(hits_key.items()):
        vs = ", ".join(f"0x{v:08X}" for v in val)
        print(f"  value [{vs}]  x{len(lst)}")
        for t, g, i, base, name in lst[:6]:
            print(f"        {{T=0x{t:08X}, G=0x{g:08X}, I=0x{i:08X}}} "
                  f"[{base}] {name!r}")
        if len(lst) > 6:
            print(f"        ... {len(lst) - 6} more")

    print(f"\n== carriers of 0x4A70D491 (the VETO property): "
          f"{len(hits_veto)} ==")
    for t, g, i, base, name in hits_veto[:40]:
        print(f"  {{T=0x{t:08X}, G=0x{g:08X}, I=0x{i:08X}}} [{base}] {name!r}")


if __name__ == "__main__":
    main()
