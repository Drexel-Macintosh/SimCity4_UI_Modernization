# V5: runtime-log null check for the GZ tooltip window 0x82F0121D, with the tip layer
# 0x2AAB8CC1 as positive control. Reads _tests\captures (read-only).
import os, re
root = r"C:\dev\SC4UIScale\_tests\captures"
files = []
for dp, dn, fn in os.walk(root):
    for f in fn:
        files.append(os.path.join(dp, f))
n_files = len(files)
hits_gz = []
enum_total = 0
enum_with_tip = 0
enum_tip_vt = {}
files_with_mwkid = 0
top_re = re.compile(r'MWKID\s+(\d+)\s+id=0x([0-9A-Fa-f]{8})\s+vt=([0-9A-Fa-f]{8})')
for f in files:
    try:
        data = open(f, 'rb').read()
    except Exception:
        continue
    if b'82f0121d' in data.lower():
        hits_gz.append(f)
    if b'MWKID' not in data:
        continue
    files_with_mwkid += 1
    cur = None
    for line in data.decode('latin1').splitlines():
        m = top_re.search(line)
        if not m:
            continue
        idx = int(m.group(1)); cid = m.group(2).upper(); vt = m.group(3).upper()
        if idx == 0:
            if cur is not None:
                enum_total += 1
                if cur['tip']:
                    enum_with_tip += 1
            cur = {'tip': False}
        if cur is None:
            cur = {'tip': False}
        if cid == '2AAB8CC1':
            cur['tip'] = True
            enum_tip_vt[vt] = enum_tip_vt.get(vt, 0) + 1
        if cid == '82F0121D':
            cur['gz'] = True
    if cur is not None:
        enum_total += 1
        if cur['tip']:
            enum_with_tip += 1
print('files scanned', n_files, 'files with MWKID', files_with_mwkid)
print('files containing 82F0121D:', len(hits_gz), hits_gz[:5])
print('top-level enumerations', enum_total, 'with 2AAB8CC1', enum_with_tip)
print('2AAB8CC1 vt values seen', enum_tip_vt)
