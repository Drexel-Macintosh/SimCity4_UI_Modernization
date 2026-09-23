# Independent vtable-length measurement.
# For each claimed vtable: count consecutive entries that point into executable
# code, report the first non-code dword, and any address inside the run that
# code references (i.e. could be the start of another table).
from v_refs import load

p, refs = load()

CLAIMS = [
 ('cGZWin base', 0xADC8D8, 151), ('AlertBorder', 0xAB5B48, 151), ('Text', 0xADFEB8, 151),
 ('BMP', 0xADF6A0, 151), ('Btn +4', 0xADDAF0, 151), ('RCI +4', 0xAB8628, 151), ('Grid +4', 0xADD7B0, 151),
 ('TextEdit', 0xADFBD0, 156), ('LineInput', 0xAE0FB0, 151), ('FlatRect', 0xAE20A0, 151),
 ('MiniMap', 0xAB83B8, 151), ('Custom', 0xAD6AA0, 151), ('Slider', 0xAE04D8, 157),
 ('Scrollbar', 0xAE0810, 168), ('ListBox', 0xAE1780, 169), ('Gen', 0xADC678, 152),
]

def measure(vt, cap=400):
    n = 0
    while n < cap:
        v = p.u32(vt + 4*n)
        if not p.is_code(v):
            break
        n += 1
    first_noncode = p.u32(vt + 4*n)
    inner = [(k, vt + 4*k) for k in range(1, n+1) if (vt + 4*k) in refs]
    return n, first_noncode, inner

if __name__ == '__main__':
    for name, vt, claim in CLAIMS:
        n, fnc, inner = measure(vt)
        # the table ends at the first inner referenced address, else at the first non-code dword
        end = inner[0][0] if inner else n
        print('%-12s vt %08X  code-run %3d  first-noncode %08X  inner-refs %s  => len %d  claim %d  %s' % (
            name, vt, n, fnc, ['slot%d=%08X' % x for x in inner[:4]], end, claim, 'OK' if end == claim else 'MISMATCH'))
