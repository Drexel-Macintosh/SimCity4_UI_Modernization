// DbpfExtract - SimCity 4 DBPF v1.0 archive extractor with QFS/RefPack decompression.
// Usage: DbpfExtract.exe <archive.dat> <outDir> [typeIdHexFilter]
//   typeIdHexFilter e.g. 0x856DDBAC (PNG/UI images). Omit to extract every entry.
// Output files: T-<type>_G-<group>_I-<instance>.png (raw entry bytes, decompressed if QFS).
// Also writes <outDir>\extract-manifest.csv with one row per extracted entry.
//
// DBPF 1.0 header (96 bytes), all little-endian:
//   0x00 "DBPF"          0x04 major(=1)   0x08 minor(=0)
//   0x18 dateCreated     0x1C dateModified
//   0x20 indexMajor(=7)  0x24 indexEntryCount  0x28 indexOffset  0x2C indexSize
//   0x30 holeCount       0x34 holeOffset  0x38 holeSize   0x3C indexMinor
// Index entry (index version 7.0, 20 bytes): TypeID, GroupID, InstanceID, FileOffset, FileSize.
// DIR record (TGI E86B1EEF/E86B1EEF/286B1F03): list of {T,G,I,decompressedSize} for compressed entries.
// QFS body: uint32 compressedSize, then 0x10 0xFB, then 3-byte big-endian uncompressed size, then codes.

using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

static class DbpfExtract
{
    struct Entry
    {
        public uint Type, Group, Instance, Offset, Size;
    }

    static int Main(string[] args)
    {
        if (args.Length < 2 || args.Length > 3)
        {
            Console.Error.WriteLine("Usage: DbpfExtract.exe <archive.dat> <outDir> [typeIdHexFilter]");
            Console.Error.WriteLine("  e.g. DbpfExtract.exe SimCity_1.dat out 0x856DDBAC");
            return 2;
        }

        string archivePath = args[0];
        string outDir = args[1];
        bool haveFilter = args.Length == 3;
        uint filterType = 0;
        if (haveFilter)
        {
            string f = args[2];
            if (f.StartsWith("0x", StringComparison.OrdinalIgnoreCase)) f = f.Substring(2);
            filterType = Convert.ToUInt32(f, 16);
        }

        byte[] data;
        try { data = File.ReadAllBytes(archivePath); }
        catch (Exception ex)
        {
            Console.Error.WriteLine("ERROR reading archive: " + ex.Message);
            return 1;
        }

        if (data.Length < 96 || data[0] != 'D' || data[1] != 'B' || data[2] != 'P' || data[3] != 'F')
        {
            Console.Error.WriteLine("ERROR: not a DBPF file: " + archivePath);
            return 1;
        }

        uint verMajor    = U32(data, 0x04);
        uint verMinor    = U32(data, 0x08);
        uint indexMajor  = U32(data, 0x20);
        uint indexCount  = U32(data, 0x24);
        uint indexOffset = U32(data, 0x28);
        uint indexSize   = U32(data, 0x2C);
        uint holeCount   = U32(data, 0x30);
        uint indexMinor  = U32(data, 0x3C);

        Console.WriteLine("Archive : " + Path.GetFileName(archivePath) + "  (" + data.Length + " bytes)");
        Console.WriteLine("DBPF    : v" + verMajor + "." + verMinor +
                          "  index v" + indexMajor + "." + indexMinor +
                          "  entries=" + indexCount + "  indexOffset=0x" + indexOffset.ToString("X") +
                          "  indexSize=" + indexSize + "  holes=" + holeCount);

        int entryStride = 20; // index 7.0: T,G,I,offset,size
        if (indexSize != indexCount * entryStride)
            Console.WriteLine("WARN    : indexSize " + indexSize + " != count*20 " + (indexCount * entryStride) +
                              " (unexpected for index 7.0)");

        var entries = new Entry[indexCount];
        long p = indexOffset;
        for (int i = 0; i < indexCount; i++, p += entryStride)
        {
            entries[i].Type     = U32(data, p + 0);
            entries[i].Group    = U32(data, p + 4);
            entries[i].Instance = U32(data, p + 8);
            entries[i].Offset   = U32(data, p + 12);
            entries[i].Size     = U32(data, p + 16);
        }

        // Compressed-entry directory (DIR), if present: TGI E86B1EEF / E86B1EEF / 286B1F03
        var dirSizes = new Dictionary<string, uint>(); // "T-G-I" -> decompressed size
        foreach (var e in entries)
        {
            if (e.Type == 0xE86B1EEF)
            {
                long q = e.Offset;
                long end = e.Offset + e.Size;
                while (q + 16 <= end)
                {
                    uint t = U32(data, q), g = U32(data, q + 4), inst = U32(data, q + 8), dsz = U32(data, q + 12);
                    dirSizes[Key(t, g, inst)] = dsz;
                    q += 16;
                }
            }
        }
        Console.WriteLine("DIR     : " + (dirSizes.Count > 0
            ? dirSizes.Count + " compressed entries listed"
            : "no compressed-entry directory present"));

        Directory.CreateDirectory(outDir);
        var manifest = new StringBuilder();
        manifest.AppendLine("TypeID,GroupID,InstanceID,Offset,RawSize,Compressed,OutSize,PngMagic,File");

        int matched = 0, extracted = 0, compressedCount = 0, pngMagicCount = 0, failures = 0;

        foreach (var e in entries)
        {
            if (haveFilter && e.Type != filterType) continue;
            if (e.Type == 0xE86B1EEF && !haveFilter) { /* still extract DIR when unfiltered */ }
            matched++;

            if ((long)e.Offset + e.Size > data.Length)
            {
                Console.Error.WriteLine("FAIL: entry " + Tgi(e) + " out of file bounds");
                failures++;
                continue;
            }

            byte[] raw = new byte[e.Size];
            Buffer.BlockCopy(data, (int)e.Offset, raw, 0, (int)e.Size);

            bool listedCompressed = dirSizes.ContainsKey(Key(e.Type, e.Group, e.Instance));
            bool looksQfs = raw.Length >= 9 && raw[4] == 0x10 && raw[5] == 0xFB &&
                            U32(raw, 0) <= (uint)raw.Length;
            byte[] outBytes = raw;
            bool wasCompressed = false;

            if (listedCompressed || looksQfs)
            {
                try
                {
                    outBytes = QfsDecompress(raw);
                    wasCompressed = true;
                    compressedCount++;
                }
                catch (Exception ex)
                {
                    if (listedCompressed)
                    {
                        Console.Error.WriteLine("FAIL: QFS decompress " + Tgi(e) + ": " + ex.Message);
                        failures++;
                        continue;
                    }
                    // signature false-positive: keep raw bytes
                    outBytes = raw;
                }
            }

            bool png = outBytes.Length >= 4 && outBytes[0] == 0x89 && outBytes[1] == 0x50 &&
                       outBytes[2] == 0x4E && outBytes[3] == 0x47;
            if (png) pngMagicCount++;

            string name = "T-" + e.Type.ToString("x8") + "_G-" + e.Group.ToString("x8") +
                          "_I-" + e.Instance.ToString("x8") + ".png";
            string outPath = Path.Combine(outDir, name);
            try
            {
                File.WriteAllBytes(outPath, outBytes);
                extracted++;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("FAIL: write " + name + ": " + ex.Message);
                failures++;
                continue;
            }

            manifest.AppendLine("0x" + e.Type.ToString("X8") + ",0x" + e.Group.ToString("X8") +
                                ",0x" + e.Instance.ToString("X8") + "," + e.Offset + "," + e.Size + "," +
                                (wasCompressed ? "yes" : "no") + "," + outBytes.Length + "," +
                                (png ? "yes" : "no") + "," + name);
        }

        File.WriteAllText(Path.Combine(outDir, "extract-manifest.csv"), manifest.ToString());

        Console.WriteLine("Matched : " + matched + (haveFilter ? "  (type 0x" + filterType.ToString("X8") + ")" : "  (all types)"));
        Console.WriteLine("Extract : " + extracted + "  compressed=" + compressedCount +
                          "  pngMagic=" + pngMagicCount + "  failures=" + failures);
        return failures == 0 ? 0 : 1;
    }

    // EA RefPack / QFS decompression. Body: uint32 LE compressed size, 0x10 0xFB,
    // 3-byte big-endian uncompressed size, then control codes.
    static byte[] QfsDecompress(byte[] src)
    {
        int pos;
        if (src.Length >= 9 && src[4] == 0x10 && src[5] == 0xFB) pos = 4;       // SC4 layout: 4-byte size prefix
        else if (src.Length >= 5 && src[0] == 0x10 && src[1] == 0xFB) pos = 0;  // bare RefPack
        else throw new InvalidDataException("no QFS 0x10FB signature");

        pos += 2;
        int outLen = (src[pos] << 16) | (src[pos + 1] << 8) | src[pos + 2];
        pos += 3;

        byte[] dst = new byte[outLen];
        int outPos = 0;

        while (pos < src.Length && outPos < outLen)
        {
            int c0 = src[pos++];
            int numPlain, numCopy, copyOffset;

            if (c0 < 0x80)
            {
                // 2-byte code
                int c1 = src[pos++];
                numPlain   = c0 & 0x03;
                numCopy    = ((c0 & 0x1C) >> 2) + 3;
                copyOffset = ((c0 & 0x60) << 3) + c1 + 1;
            }
            else if (c0 < 0xC0)
            {
                // 3-byte code
                int c1 = src[pos++], c2 = src[pos++];
                numPlain   = (c1 & 0xC0) >> 6;
                numCopy    = (c0 & 0x3F) + 4;
                copyOffset = ((c1 & 0x3F) << 8) + c2 + 1;
            }
            else if (c0 < 0xE0)
            {
                // 4-byte code
                int c1 = src[pos++], c2 = src[pos++], c3 = src[pos++];
                numPlain   = c0 & 0x03;
                numCopy    = ((c0 & 0x0C) << 6) + c3 + 5;
                copyOffset = ((c0 & 0x10) << 12) + (c1 << 8) + c2 + 1;
            }
            else if (c0 < 0xFC)
            {
                // literal run
                numPlain   = ((c0 & 0x1F) + 1) << 2;
                numCopy    = 0;
                copyOffset = 0;
            }
            else
            {
                // stop code
                numPlain   = c0 & 0x03;
                numCopy    = 0;
                copyOffset = 0;
                CopyPlain(src, ref pos, dst, ref outPos, numPlain);
                break;
            }

            CopyPlain(src, ref pos, dst, ref outPos, numPlain);

            // overlapping LZ copy from output history, byte by byte
            int from = outPos - copyOffset;
            if (numCopy > 0 && from < 0) throw new InvalidDataException("copy offset before start");
            for (int i = 0; i < numCopy; i++)
            {
                if (outPos >= outLen) throw new InvalidDataException("output overrun");
                dst[outPos++] = dst[from++];
            }
        }

        if (outPos != outLen)
            throw new InvalidDataException("decompressed " + outPos + " != expected " + outLen);
        return dst;
    }

    static void CopyPlain(byte[] src, ref int pos, byte[] dst, ref int outPos, int n)
    {
        if (n == 0) return;
        if (pos + n > src.Length || outPos + n > dst.Length)
            throw new InvalidDataException("plain copy overrun");
        Buffer.BlockCopy(src, pos, dst, outPos, n);
        pos += n;
        outPos += n;
    }

    static uint U32(byte[] b, long o)
    {
        return (uint)(b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24));
    }

    static string Key(uint t, uint g, uint i) { return t.ToString("X8") + "-" + g.ToString("X8") + "-" + i.ToString("X8"); }
    static string Tgi(Entry e) { return "T:0x" + e.Type.ToString("X8") + " G:0x" + e.Group.ToString("X8") + " I:0x" + e.Instance.ToString("X8"); }
}
