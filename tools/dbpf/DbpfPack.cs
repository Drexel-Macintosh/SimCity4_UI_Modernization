// DbpfPack.cs — DBPF v1.0 WRITER for SimCity 4 override packages (+ --list / --extract for verification).
//
//   DbpfPack.exe <inDir> <out.dat>            pack folder of T-0x########_G-0x########_I-0x########.* files
//   DbpfPack.exe --list <archive.dat>         dump header + index of any DBPF 1.x archive
//   DbpfPack.exe --extract <archive.dat> <outDir>   extract RAW payloads (no QFS decompression) for roundtrip proof
//
// Format (verified byte-for-byte against the retail SimCity_1.dat header):
//   Header, 96 bytes, all fields uint32 LE:
//     0x00  magic "DBPF"
//     0x04  major version   = 1
//     0x08  minor version   = 0
//     0x0C  unknown1        = 0
//     0x10  unknown2        = 0
//     0x14  unknown3        = 0
//     0x18  date created    (unix time)
//     0x1C  date modified   (unix time)
//     0x20  index major     = 7
//     0x24  index entry count
//     0x28  index offset    (absolute file offset of first index entry)
//     0x2C  index size      (bytes = count * 20)
//     0x30  hole count      = 0
//     0x34  hole offset     = 0
//     0x38  hole size       = 0
//     0x3C  index minor     = 0   (7.0)
//     0x40..0x5F reserved   = 0
//   Index entry (index version 7.0), 20 bytes:
//     TypeID, GroupID, InstanceID, file offset, file size  (all uint32 LE)
//   All payloads written UNCOMPRESSED; therefore NO compression directory
//   (DIR, TGI E86B1EEE/E86B1EEE/286B1F03) entry is written — it must simply be absent.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;

static class DbpfPack
{
    const uint IndexMajor = 7;
    const uint IndexMinor = 0;
    const int HeaderSize = 96;
    const int IndexEntrySize = 20;
    // Compression directory TGI (must NOT appear in an all-uncompressed archive)
    const uint DirType = 0xE86B1EEE, DirGroup = 0xE86B1EEE, DirInstance = 0x286B1F03;

    struct Entry
    {
        public uint Type, Group, Instance, Offset, Size;
        public string SourcePath; // pack mode only
    }

    static int Main(string[] args)
    {
        try
        {
            if (args.Length == 2 && args[0] == "--list") return List(args[1]);
            if (args.Length == 3 && args[0] == "--extract") return Extract(args[1], args[2]);
            if (args.Length == 2 && !args[0].StartsWith("--")) return Pack(args[0], args[1]);
            Console.Error.WriteLine("DbpfPack — DBPF v1.0 writer for SimCity 4 override packages");
            Console.Error.WriteLine("usage: DbpfPack.exe <inDir> <out.dat>");
            Console.Error.WriteLine("       DbpfPack.exe --list <archive.dat>");
            Console.Error.WriteLine("       DbpfPack.exe --extract <archive.dat> <outDir>   (raw payloads, no QFS decompression)");
            return 2;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("ERROR: " + ex.Message);
            return 1;
        }
    }

    // ---------------- pack ----------------

    static readonly Regex TgiName = new Regex(
        @"^T-0x(?<t>[0-9A-Fa-f]{8})_G-0x(?<g>[0-9A-Fa-f]{8})_I-0x(?<i>[0-9A-Fa-f]{8})(\.[^.]+)?$",
        RegexOptions.Compiled);

    static int Pack(string inDir, string outPath)
    {
        if (!Directory.Exists(inDir))
            throw new IOException("input directory not found: " + inDir);

        var entries = new List<Entry>();
        var seen = new Dictionary<string, string>();
        int skipped = 0;
        foreach (string path in Directory.GetFiles(inDir))
        {
            string name = Path.GetFileName(path);
            Match m = TgiName.Match(name);
            if (!m.Success)
            {
                Console.Error.WriteLine("skip (name not T-0x…_G-0x…_I-0x…): " + name);
                skipped++;
                continue;
            }
            var e = new Entry
            {
                Type = uint.Parse(m.Groups["t"].Value, NumberStyles.HexNumber),
                Group = uint.Parse(m.Groups["g"].Value, NumberStyles.HexNumber),
                Instance = uint.Parse(m.Groups["i"].Value, NumberStyles.HexNumber),
                SourcePath = path
            };
            string key = e.Type.ToString("X8") + e.Group.ToString("X8") + e.Instance.ToString("X8");
            if (seen.ContainsKey(key))
                throw new IOException("duplicate TGI: " + name + " collides with " + seen[key]);
            seen[key] = name;
            if (e.Type == DirType && e.Group == DirGroup && e.Instance == DirInstance)
                throw new IOException("refusing to pack a compression directory (DIR) entry; this tool writes uncompressed archives only: " + name);
            entries.Add(e);
        }
        if (entries.Count == 0)
            throw new IOException("no T-0x…_G-0x…_I-0x… files found in " + inDir);

        // deterministic output: sort by Type, Group, Instance
        entries.Sort((a, b) =>
        {
            int c = a.Type.CompareTo(b.Type);
            if (c != 0) return c;
            c = a.Group.CompareTo(b.Group);
            return c != 0 ? c : a.Instance.CompareTo(b.Instance);
        });

        uint now = (uint)(DateTime.UtcNow - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;

        using (var fs = new FileStream(outPath, FileMode.Create, FileAccess.Write))
        using (var w = new BinaryWriter(fs))
        {
            // placeholder header; rewritten after we know the index position
            w.Write(new byte[HeaderSize]);

            for (int i = 0; i < entries.Count; i++)
            {
                byte[] data = File.ReadAllBytes(entries[i].SourcePath);
                if (fs.Position > uint.MaxValue - (long)data.Length)
                    throw new IOException("archive would exceed the 4 GiB DBPF uint32 offset limit");
                Entry e = entries[i];
                e.Offset = (uint)fs.Position;
                e.Size = (uint)data.Length;
                entries[i] = e;
                w.Write(data);
            }

            uint indexOffset = (uint)fs.Position;
            foreach (Entry e in entries)
            {
                w.Write(e.Type);
                w.Write(e.Group);
                w.Write(e.Instance);
                w.Write(e.Offset);
                w.Write(e.Size);
            }
            uint indexSize = (uint)(entries.Count * IndexEntrySize);

            fs.Position = 0;
            w.Write(System.Text.Encoding.ASCII.GetBytes("DBPF"));
            w.Write(1u);            // 0x04 major
            w.Write(0u);            // 0x08 minor
            w.Write(0u);            // 0x0C unknown1
            w.Write(0u);            // 0x10 unknown2
            w.Write(0u);            // 0x14 unknown3
            w.Write(now);           // 0x18 date created
            w.Write(now);           // 0x1C date modified
            w.Write(IndexMajor);    // 0x20 index major = 7
            w.Write((uint)entries.Count); // 0x24 index count
            w.Write(indexOffset);   // 0x28 index offset
            w.Write(indexSize);     // 0x2C index size
            w.Write(0u);            // 0x30 hole count
            w.Write(0u);            // 0x34 hole offset
            w.Write(0u);            // 0x38 hole size
            w.Write(IndexMinor);    // 0x3C index minor = 0
            // 0x40..0x5F reserved zeros already written by placeholder
        }

        Console.WriteLine("packed {0} file(s) ({1} skipped) -> {2}", entries.Count, skipped, outPath);
        Console.WriteLine("index 7.{0} @ 0x{1:X}, {2} bytes, all entries uncompressed, no DIR record",
            IndexMinor, new FileInfo(outPath).Length - entries.Count * IndexEntrySize, entries.Count * IndexEntrySize);
        return 0;
    }

    // ---------------- shared reader ----------------

    static List<Entry> ReadIndex(string path, out uint[] header)
    {
        using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read))
        using (var r = new BinaryReader(fs))
        {
            if (fs.Length < HeaderSize) throw new IOException("file too small to be DBPF");
            byte[] magic = r.ReadBytes(4);
            if (magic[0] != 'D' || magic[1] != 'B' || magic[2] != 'P' || magic[3] != 'F')
                throw new IOException("not a DBPF file (bad magic)");
            header = new uint[23];
            for (int i = 0; i < 23; i++) header[i] = r.ReadUInt32();

            uint count = header[8];       // 0x24
            uint indexOffset = header[9]; // 0x28
            uint indexSize = header[10];  // 0x2C
            if ((long)indexOffset + indexSize > fs.Length)
                throw new IOException("index extends past end of file");
            if (indexSize != count * IndexEntrySize)
                Console.Error.WriteLine("warning: index size 0x{0:X} != count {1} * 20", indexSize, count);

            var list = new List<Entry>((int)count);
            fs.Position = indexOffset;
            for (uint i = 0; i < count; i++)
            {
                var e = new Entry
                {
                    Type = r.ReadUInt32(),
                    Group = r.ReadUInt32(),
                    Instance = r.ReadUInt32(),
                    Offset = r.ReadUInt32(),
                    Size = r.ReadUInt32()
                };
                list.Add(e);
            }
            return list;
        }
    }

    static int List(string path)
    {
        uint[] h;
        List<Entry> entries = ReadIndex(path, out h);
        Console.WriteLine("archive : {0}  ({1} bytes)", path, new FileInfo(path).Length);
        Console.WriteLine("version : DBPF {0}.{1}   index {2}.{3}", h[0], h[1], h[7], h[14]);
        Console.WriteLine("dates   : created 0x{0:X8}  modified 0x{1:X8}", h[5], h[6]);
        Console.WriteLine("index   : {0} entries @ 0x{1:X} ({2} bytes)", h[8], h[9], h[10]);
        Console.WriteLine("holes   : {0} @ 0x{1:X} ({2} bytes)", h[11], h[12], h[13]);
        bool hasDir = false;
        foreach (Entry e in entries)
            if (e.Type == DirType && e.Group == DirGroup && e.Instance == DirInstance) hasDir = true;
        Console.WriteLine("DIR     : compression directory {0}", hasDir ? "PRESENT (some entries QFS-compressed)" : "absent (all uncompressed)");
        Console.WriteLine();
        Console.WriteLine("TypeID     GroupID    InstanceID Offset     Size");
        foreach (Entry e in entries)
            Console.WriteLine("0x{0:X8} 0x{1:X8} 0x{2:X8} 0x{3:X8} {4}", e.Type, e.Group, e.Instance, e.Offset, e.Size);
        return 0;
    }

    static int Extract(string path, string outDir)
    {
        uint[] h;
        List<Entry> entries = ReadIndex(path, out h);
        Directory.CreateDirectory(outDir);
        using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read))
        {
            foreach (Entry e in entries)
            {
                var data = new byte[e.Size];
                fs.Position = e.Offset;
                int read = 0;
                while (read < data.Length)
                {
                    int n = fs.Read(data, read, data.Length - read);
                    if (n <= 0) throw new IOException("short read in payload");
                    read += n;
                }
                string name = string.Format("T-0x{0:X8}_G-0x{1:X8}_I-0x{2:X8}.bin", e.Type, e.Group, e.Instance);
                File.WriteAllBytes(Path.Combine(outDir, name), data);
            }
        }
        Console.WriteLine("extracted {0} raw payload(s) -> {1}  (no QFS decompression applied)", entries.Count, outDir);
        return 0;
    }
}
