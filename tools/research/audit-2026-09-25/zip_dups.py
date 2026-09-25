"""Which files in the release zip are byte-identical copies of each other (CRC32 + size)?

    python zip_dups.py [path\to\SC4UIScale-vX.Y.Z.zip]
"""
import collections
import sys
import zipfile

ZIP = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\SC4UIScale\dist\SC4UIScale-v4.10.2.zip"
z = zipfile.ZipFile(ZIP)
groups = collections.defaultdict(list)
for i in z.infolist():
    if i.file_size:
        groups[(i.CRC, i.file_size)].append(i)
extra = 0
total = sum(i.compress_size for i in z.infolist())
for (crc, size), items in sorted(groups.items(), key=lambda kv: -kv[0][1]):
    if len(items) < 2:
        continue
    extra += sum(i.compress_size for i in items[1:])
    names = [i.filename.split("Plugins/", 1)[-1] for i in items]
    if size > 64 * 1024:
        print("%8.1f MB x%d: %s" % (size / 1e6, len(items), " | ".join(names)))
print("zip %.1f MB; compressed bytes in extra copies: %.1f MB (%.0f%%)"
      % (total / 1e6, extra / 1e6, 100.0 * extra / total))
