# rng.py - print lines of a lin.py dump whose address is in [a,b)
# usage: python rng.py file.txt 0x76DD2F 0x76DE00
import sys
f, a, b = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
for line in open(f):
    try:
        va = int(line[:10], 16)
    except ValueError:
        continue
    if a <= va < b:
        print(line.rstrip())
