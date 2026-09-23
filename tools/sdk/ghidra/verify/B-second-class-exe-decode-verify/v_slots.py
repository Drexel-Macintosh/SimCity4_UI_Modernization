# Dump slot VAs across the 15 class vtables (window part) and compare to the
# finder's claimed base VAs / override lists.
from v_pe import PE
p = PE()

VT = [('base', 0xADC8D8), ('Alert', 0xAB5B48), ('Text', 0xADFEB8), ('BMP', 0xADF6A0), ('Btn', 0xADDAF0),
      ('TE', 0xADFBD0), ('LI', 0xAE0FB0), ('RCI', 0xAB8628), ('Flat', 0xAE20A0), ('SB', 0xAE0810),
      ('Slider', 0xAE04D8), ('LB', 0xAE1780), ('Gen', 0xADC678), ('Mini', 0xAB83B8), ('Grid', 0xADD7B0),
      ('Custom', 0xAD6AA0)]

# finder's claimed base VA per slot, and claimed overrides among the 15
CLAIM = {
 50: (0x99BCE8, {}), 51: (0x99BC68, {}), 52: (0x99BC8F, {}), 53: (0x99BCB6, {}), 54: (0x9D7D97, {}),
 55: (0x99C837, {'Text': 0x9C20D3, 'BMP': 0x9BC0B8, 'Btn': 0x9B1397, 'TE': 0x9BFCA5, 'LI': 0x9C5F96, 'SB': 0x9C331A,
                 'Slider': 0x9C331A, 'LB': 0x9C870B, 'Gen': 0x99A0AF, 'Mini': 0x7A8E30, 'Grid': 0x5F8FC0}),
 56: (0x99C8C5, {}), 57: (0x99BD27, {}), 58: (0x99C3DF, {}), 59: (0x99BD73, {}), 60: (0x99BD5E, {}),
 63: (0x99BE66, {'Btn': 0x9B1D80}), 64: (0x99BE5C, {'Btn': 0x9B1D88}),
 65: (0x99BE79, {}), 66: (0x99BE6A, {}), 67: (0x99BDBB, {}),
 68: (0x99DB6B, {'Btn': 0x9B112D, 'TE': 0x9BC7DD, 'LI': 0x9C5B55, 'LB': 0x9C9379, 'Grid': 0x9A6224}),
 69: (0x99D1AA, {'TE': 0x9BE99F}), 70: (0x99D1EA, {}),
 86: (0x99BE42, {}), 87: (0x99BE4C, {}),
 88: (0x949ADE, {'Alert': 0x794100, 'Text': 0x9C1A9A, 'BMP': 0x9BC325, 'Btn': 0x9B167D, 'TE': 0x9BEA28, 'LI': 0x9C6B03,
                 'RCI': 0x7A9500, 'Flat': 0x9CD1FF, 'SB': 0x9C453D, 'Slider': 0x9C3623, 'LB': 0x9CA19A, 'Gen': 0x9995E7,
                 'Mini': 0x7A79B0, 'Grid': 0x9AF168, 'Custom': 0x95BA43}),
 89: (0x99BA07, {}), 115: (0x99D252, {}), 116: (0x99D832, {}), 117: (0x99D865, {}),
 118: (0x99BD13, {}), 119: (0x99C373, {}), 120: (0x99C303, {}), 121: (0x99C8F5, {'Gen': 0x99955D}),
 122: (0x99C960, {}), 123: (0x99E62D, {}), 124: (0x99C498, {}), 125: (0x99BF6D, {}), 126: (0x99BFA5, {}),
 127: (0x99BB08, {}), 128: (0x99BB5A, {}),
 129: (0x93878E, {'TE': 0x9C0996, 'LI': 0x9C6F5A, 'Grid': 0x9A5F1E}),
 130: (0x93877E, None), 131: (0x93877E, None),
 132: (0x99CF49, {'TE': 0x9BC75D, 'LI': 0x9C5DD5, 'Grid': 0x9A7E0C}),
 133: (0x93878E, {'TE': 0x9BC79D, 'LI': 0x9C5DEF, 'Grid': 0x9A7E2F}),
 134: (0x9378BC, None), 135: (0x9378BC, {'Btn': 0x9B17EF, 'TE': 0x9BC6D8, 'Mini': 0x49C7B0}),
 136: (0x9378BC, None), 137: (0x9378BC, {'Btn': 0x9B1923}), 138: (0x9378BC, None),
 139: (0x938789, {'TE': 0x9BC705, 'Grid': 0x9A5F7D}), 140: (0x93877E, {'Btn': 0x9B19FF}),
 141: (0x93878E, {'Btn': 0x9B1BE4, 'Mini': 0x7A66B0}), 142: (0x93878E, {'Btn': 0x9B19E0, 'Mini': 0x7A66B0}),
 143: (0x93877E, {'Gen': 0x999896}), 144: (0x99CA2F, {}), 145: (0x99BFEC, {}), 146: (0x99CA60, {}),
 147: (0x99C011, {}), 148: (0x9D060A, None), 149: (0x99BBBE, {}), 150: (0x99D0ED, {}),
}

def row(slot):
    return {n: p.u32(vt + 4*slot) for n, vt in VT}

if __name__ == '__main__':
    bad = 0
    for slot in sorted(CLAIM):
        base_claim, ov = CLAIM[slot]
        r = row(slot)
        issues = []
        if r['base'] != base_claim:
            issues.append('BASE %08X != claim %08X' % (r['base'], base_claim))
        overrides = {n: v for n, v in r.items() if n != 'base' and v != r['base']}
        if ov is not None:
            if overrides != ov:
                issues.append('OVR measured %s vs claim %s' % (
                    {k: '%X' % v for k, v in overrides.items()}, {k: '%X' % v for k, v in ov.items()}))
        print('slot %3d base %08X  overrides(%2d): %s %s' % (slot, r['base'], len(overrides),
              ' '.join('%s=%X' % (k, v) for k, v in overrides.items()), ('  <<< ' + '; '.join(issues)) if issues else ''))
        bad += bool(issues)
    print('slots with discrepancies:', bad)
