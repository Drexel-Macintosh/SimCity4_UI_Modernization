#!/usr/bin/env python3
r"""Locate the INTRO VIDEO / SPLASH window classes in SimCity 4.exe, statically.

WHY. 2026-08-05: the intro video (800x608, Intro.dat I-00000001) draws at its
native size on a 2400x1600 screen, while the EA logo clip (512x384,
I-00000002) fills. Same format, same archive, same decoder - so something on
that path already stretches, and the logo is a live existence proof.

tools\sdk\lookup.py reports 0x2A3832AA (cSC4WinIntroVideoScreen) absent from
our source, absent from the .UI corpus, and unshipped by us - with positive
controls proving those scans CAN find things. So it is CODE-BOUND: the sizing
lives in the exe, not in data.

DYNAMIC-CONTROLS.md:60 records the way in - every window class is registered in
ONE function at VA 0x4662B0 with the pattern

    push <factory>          68 xx xx xx xx
    push <clsid>            68 xx xx xx xx
    mov  ecx, esi           8B CE
    call 0x90E133           E8 xx xx xx xx

so scanning that function for `push <clsid>` and reading the push immediately
before it recovers the factory address for any class id.

Read-only. Never writes to the game directory.

    python find_intro_video.py
"""
import os
import struct
import sys

GAME_EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"

# Classes we care about, plus CONTROLS - ids DYNAMIC-CONTROLS.md already
# resolved by hand. If the scan cannot find these, the scan is broken and any
# null for the intro classes means nothing (feedback-null-is-not-evidence).
TARGETS = {
    0x2A3832AA: "cSC4WinIntroVideoScreen   <- the one we want",
    0xAA38326E: "cSC4WinSplashScreen       <- plays the other clip?",
}
CONTROLS = {
    0xC7A0E17E: "cSC4WinRCI            (control: factory should be 0x466170)",
    0xAA5C2F86: "cSC4WinTrendBar       (control: factory should be 0x4661A0)",
    0x89E1567C: "cSC4WinGenTransparent (control: factory should be 0x4661D0)",
}


def load_sections(path):
    with open(path, "rb") as f:
        data = f.read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        sys.exit("not a PE file")
    n_sec = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    image_base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    sec_off = pe + 24 + opt_size
    secs = []
    for i in range(n_sec):
        o = sec_off + i * 40
        name = data[o:o + 8].rstrip(b"\0").decode("latin1")
        vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", data, o + 8)
        secs.append((name, vaddr, vsize, raddr, rsize))
    return data, image_base, secs


def va_to_off(va, image_base, secs):
    rva = va - image_base
    for name, vaddr, vsize, raddr, rsize in secs:
        if vaddr <= rva < vaddr + max(vsize, rsize):
            return raddr + (rva - vaddr)
    return None


def main():
    if not os.path.isfile(GAME_EXE):
        sys.exit("exe not found: %s" % GAME_EXE)
    data, base, secs = load_sections(GAME_EXE)
    print("exe        : %s (%d bytes)" % (os.path.basename(GAME_EXE), len(data)))
    print("image base : 0x%08X" % base)
    for name, vaddr, vsize, raddr, rsize in secs:
        print("  %-8s VA 0x%08X  vsize %8d  raw 0x%08X" % (name, base + vaddr, vsize, raddr))

    # Scan the WHOLE image for `push <clsid>` rather than only the registration
    # function - a class may also be referenced by CreateInstance elsewhere, and
    # we want every site, not just the registrar.
    print("\n%s\nCLSID PUSH SITES  (68 <imm32>)\n%s" % ("=" * 74, "=" * 74))
    for clsid, label in list(TARGETS.items()) + list(CONTROLS.items()):
        pat = b"\x68" + struct.pack("<I", clsid)
        hits = []
        start = 0
        while True:
            k = data.find(pat, start)
            if k < 0:
                break
            hits.append(k)
            start = k + 1
        print("\n0x%08X  %s" % (clsid, label))
        if not hits:
            print("   (no push site found)")
            continue
        for off in hits:
            # recover VA of this instruction
            va = None
            for name, vaddr, vsize, raddr, rsize in secs:
                if raddr <= off < raddr + rsize:
                    va = base + vaddr + (off - raddr)
                    break
            prev = data[max(0, off - 5):off]
            factory = None
            if len(prev) == 5 and prev[0] == 0x68:
                factory = struct.unpack_from("<I", prev, 1)[0]
            nxt = data[off + 5:off + 12]
            print("   site VA 0x%08X (file 0x%06X)%s  next: %s"
                  % (va or 0, off,
                     ("  factory=0x%08X" % factory) if factory else "",
                     " ".join("%02X" % c for c in nxt)))


if __name__ == "__main__":
    main()
