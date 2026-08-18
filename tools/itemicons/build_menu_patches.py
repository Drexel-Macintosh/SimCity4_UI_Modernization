#!/usr/bin/env python3
"""Build z_SC4UIScale_MenuFix.dat - exemplar patches restoring CAM's lost items.

THIRD-PARTY DATA PATCH - this dat modifies ANOTHER MOD'S content at runtime.
It exists because CAM 4.0.1 (SC4 System Integration Module) ships 10 catalog
items with broken submenu parents, making them unreachable in game (found by
scan_unreachable_items.py, 2026-07-29):

  * 9 buildings in "2 CAM Building\\CAM_Police_Fire_Buildings.dat" carry
    Item Submenu Parent (0xAA1DD399) = {0x00000000} - a null menu. Affected:
    Police Kiosk, 4-car + 36-car precincts, Deluxe Precinct, Jail, Prison,
    and three fire stations.
  * The Lifeguard Tower in CAM_Park_Buildings.dat points at submenu
    0x1C3780E4, which no installed plugin defines.

REPORT UPSTREAM: tools/research/UPSTREAM-CAM-REPORT.md is the write-up for
the CAM developers. If a CAM update fixes these, DELETE this dat and re-run
the scanner to confirm.

MECHANISM: Exemplar Patch cohorts as defined by sc4-resource-loading-hooks
(installed as SC4ResourceLoadingHooks.dll): a Cohort (type 0x05342861) in
group 0xB03697D1 whose property 0x0062E78A lists target exemplars as
(GroupID, InstanceID) pairs; every OTHER property (except the name, 0x20) is
injected into the targets at load. We inject only 0xAA1DD399, re-pointing
each item at a menu that exists:

  target submenu ids (from the submenus package, all defined + visible):
    police-small  0x65D88585   police-large 0x7D6DC8BC
    police-deluxe 0x8157CA0E
  physical menu roots (always in the DLL's reachable set - verified in
  submenus-dll source, `reachableSubmenus(toplevelMenuButtons)`):
    police 0x37   fire 0x38   parks 0x3

Run from tools/itemicons:  python build_menu_patches.py
Output: _work/menufix/ (cohort files) + _work/z_SC4UIScale_MenuFix.dat.
Deploy to Plugins\\zzz-SC4UIScale\\ (subfolder REQUIRED: root files load
before subfolders and would lose to CAM's 050-load-first dats).
"""
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '_work', 'menufix')
DAT = os.path.join(HERE, '_work', 'z_SC4UIScale_MenuFix.dat')
PACK = os.path.join(HERE, '..', 'dbpf', 'DbpfPack.exe')

COHORT_TYPE = 0x05342861
PATCH_GROUP = 0xB03697D1
PROP_NAME = 0x00000020
PROP_TARGETS = 0x0062E78A
PROP_SUBMENU_PARENT = 0xAA1DD399

# (instance, name, [(targetGroup, targetInstance), ...], [parent ids])
PATCHES = [
    (0x5C4F1201, 'UIScale_MenuFix_PoliceSmall',
     [(0x07BDDF1C, 0x5D621FE4),   # CV9X7_PoliceKiosk_PIMxD
      (0x07BDDF1C, 0xD1CE0B65)],  # CV24X24_4carLocalPrecinct_PIMxD
     [0x65D88585]),
    (0x5C4F1202, 'UIScale_MenuFix_PoliceLarge',
     [(0x07BDDF1C, 0x468FD65F)],  # CV32x28_36carLocalPrecinct_PIMxD
     [0x7D6DC8BC]),
    (0x5C4F1203, 'UIScale_MenuFix_PoliceDeluxe',
     [(0x07BDDF1C, 0xACCCDC74)],  # CV40x36_DeluxePrecinct_PIMxD
     [0x8157CA0E]),
    (0x5C4F1204, 'UIScale_MenuFix_JailPrison',
     [(0x07BDDF1C, 0xA2B88DC7),   # CV38x48_Jail_PIMxD
      (0x8A3858D8, 0x21483528)],  # RW64x64_Prison_PIMxD
     [0x37]),                     # police menu root (no jail submenu exists)
    (0x5C4F1205, 'UIScale_MenuFix_FireStations',
     [(0x07BDDF1C, 0x640875EE),   # CV12x14_2engineStationHouse_PIMxD
      (0x07BDDF1C, 0xD7C564C4),   # CV32x32_4engineStationHouse_PIMxD
      (0x07BDDF1C, 0xA3DB5600)],  # CV19x15_DeluxeFireStation_PIMxD
     [0x38]),                     # fire menu root (no fire submenus exist)
    (0x5C4F1206, 'UIScale_MenuFix_LifeguardTower',
     [(0x358BADF0, 0x6387BEB8)],  # PZPark3x6x5_Lifeguardtower_1DDD_PIM-Xd
     [0x3]),                      # parks menu root (0x1C3780E4 is undefined)
]


def prop_uint32_array(prop_id, values):
    # per the EQZB/CQZB format (ITEMICONS.md appendix): id u32, valType u16
    # (0x300 = uint32), keyType u16 (0x80 = array), 1 pad byte, u32 rep, values
    out = struct.pack('<IHHBI', prop_id, 0x300, 0x80, 0, len(values))
    for v in values:
        out += struct.pack('<I', v)
    return out


def prop_string(prop_id, text):
    b = text.encode('ascii')
    return struct.pack('<IHHBI', prop_id, 0xC00, 0x80, 0, len(b)) + b


def build_cohort(name, targets, parents):
    props = [
        prop_string(PROP_NAME, name),
        prop_uint32_array(PROP_TARGETS,
                          [v for gi in targets for v in gi]),
        prop_uint32_array(PROP_SUBMENU_PARENT, parents),
    ]
    body = b'CQZB1###' + struct.pack('<III', 0, 0, 0)
    body += struct.pack('<I', len(props))
    for p in props:
        body += p
    return body


def main():
    os.makedirs(OUT, exist_ok=True)
    for inst, name, targets, parents in PATCHES:
        data = build_cohort(name, targets, parents)
        fn = os.path.join(
            OUT, f'T-0x{COHORT_TYPE:08x}_G-0x{PATCH_GROUP:08x}_I-0x{inst:08x}.bin')
        with open(fn, 'wb') as fh:
            fh.write(data)
        print(f'{name}: {len(targets)} target(s) -> '
              f'{["0x%08X" % p for p in parents]}  ({len(data)} bytes)')
    r = subprocess.run([PACK, OUT, DAT], capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
