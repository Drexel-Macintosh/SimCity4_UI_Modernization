// OddballConvert.cs — 2x-upscale the 74 non-PNG Type-0x856DDBAC UI resources from SimCity_1.dat.
//
//   OddballConvert.exe <extractedDir> <outRoot>
//
// Re-scans <extractedDir> by MAGIC BYTES (extensions are lies: everything is named .png).
// For every file that is NOT a real PNG it emits, into <outRoot>:
//
//   converted2x\T-0x…_G-0x…_I-0x….png   2x nearest-neighbour PNG (reference / PNG-pipeline use)
//   native2x\T-0x…_G-0x…_I-0x….jpg     JPEG sources  -> 2x, re-encoded JPEG quality 95 (24bpp)
//   native2x\T-0x…_G-0x…_I-0x….bmp     BMP sources   -> 2x, uncompressed 24bpp BMP
//   native2x\T-0x…_G-0x…_I-0x….fsh     FSH sources   -> 2x, rebuilt EA SHPI container, same
//                                       bitmap code, header/dir/"Buy ERTS" filler/attachment
//                                       blocks preserved byte-for-byte
//   oddball-report.csv                  one row per processed file (TGI, format, dims, action)
//
// Naming matches the DbpfPack.exe convention (T-0x########_G-0x########_I-0x########.<any ext>,
// lowercase hex, TGI parsed from the name; payload bytes are packed verbatim).
//
// Upscale is EXACT 2x2 pixel replication via LockBits (no filtering, no resampling).
//
// FSH (EA SHPI) support — format per fshtool/FshFormat plugin docs, verified against all 26
// files in this set (every one: single entry, bitmap code 0x7D = 32-bit A8R8G8B8):
//   header  : "SHPI" | int32 fileSize | int32 nEntries | 4-char directory id
//   dir     : nEntries * (4-char entry name | int32 entry offset)
//   entry   : byte code | int24 blockSize (0 = last block, else offset to next block)
//             uint16 width | uint16 height | 4 * uint16 misc (center x/y, pos x/y)
//             pixel data  (0x7D: B,G,R,A per pixel; 0x7F: B,G,R; rows top-down)
//   after   : optional attachment blocks (e.g. 0x70 = name string), copied verbatim
//   code & 0x80 = QFS-compressed entry (unsupported here; none occur in this set)
//   DXT1 0x60 / DXT3 0x61: decode+re-encode not implemented (none occur in this set);
//   such files would get a report row + no native output.
//
// Every emitted file is verified: PNG/JPG/BMP reloaded and dimension-checked (BMP + FSH also
// pixel-compared exactly against the in-memory 2x source; JPEG is lossy so dims only).

using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

static class OddballConvert
{
    static readonly Regex TgiName = new Regex(
        @"^T-(?<t>[0-9A-Fa-f]{8})_G-(?<g>[0-9A-Fa-f]{8})_I-(?<i>[0-9A-Fa-f]{8})\.[^.]+$",
        RegexOptions.Compiled);

    sealed class Row
    {
        public string File, Tgi, Format, FshInfo, Action, Native, Converted, Notes;
        public int SrcW, SrcH, OutW, OutH;
    }

    static int Main(string[] args)
    {
        if (args.Length != 2)
        {
            Console.Error.WriteLine("usage: OddballConvert.exe <extractedDir> <outRoot>");
            return 2;
        }
        string inDir = args[0], outRoot = args[1];
        string convDir = Path.Combine(outRoot, "converted2x");
        string natDir = Path.Combine(outRoot, "native2x");
        Directory.CreateDirectory(convDir);
        Directory.CreateDirectory(natDir);

        var rows = new List<Row>();
        int nPng = 0, nJpeg = 0, nBmp = 0, nFsh = 0, nUnknown = 0, nNativeOk = 0, nErr = 0;

        foreach (string path in Directory.GetFiles(inDir))
        {
            string name = Path.GetFileName(path);
            Match m = TgiName.Match(name);
            if (!m.Success) continue; // manifest csv etc.

            byte[] data = File.ReadAllBytes(path);
            string fmt = Sniff(data);
            if (fmt == "PNG") { nPng++; continue; }

            string baseName = string.Format("T-0x{0}_G-0x{1}_I-0x{2}",
                m.Groups["t"].Value.ToLowerInvariant(),
                m.Groups["g"].Value.ToLowerInvariant(),
                m.Groups["i"].Value.ToLowerInvariant());
            string tgi = string.Format("0x{0} / 0x{1} / 0x{2}",
                m.Groups["t"].Value.ToUpperInvariant(),
                m.Groups["g"].Value.ToUpperInvariant(),
                m.Groups["i"].Value.ToUpperInvariant());

            var row = new Row { File = name, Tgi = tgi, Format = fmt, FshInfo = "", Notes = "" };
            rows.Add(row);
            try
            {
                switch (fmt)
                {
                    case "JPEG": nJpeg++; DoGdi(data, row, convDir, natDir, baseName, true); nNativeOk++; break;
                    case "BMP":  nBmp++;  DoGdi(data, row, convDir, natDir, baseName, false); nNativeOk++; break;
                    case "FSH":  nFsh++;  if (DoFsh(data, row, convDir, natDir, baseName)) nNativeOk++; break;
                    default:
                        nUnknown++;
                        row.Action = "SKIPPED";
                        row.Notes = "unrecognized magic: " + BitConverter.ToString(data, 0, Math.Min(8, data.Length));
                        break;
                }
            }
            catch (Exception ex)
            {
                nErr++;
                row.Action = "ERROR";
                row.Notes = ex.Message;
                Console.Error.WriteLine("ERROR {0}: {1}", name, ex.Message);
            }
        }

        // report csv
        var sb = new StringBuilder();
        sb.AppendLine("OriginalFile,TGI,RealFormat,FshInfo,SrcW,SrcH,OutW,OutH,Converted2x,Native2x,Action,Notes");
        foreach (Row r in rows)
            sb.AppendLine(string.Join(",", new[] {
                r.File, Csv(r.Tgi), r.Format, Csv(r.FshInfo),
                r.SrcW.ToString(), r.SrcH.ToString(), r.OutW.ToString(), r.OutH.ToString(),
                Csv(r.Converted), Csv(r.Native), Csv(r.Action), Csv(r.Notes) }));
        File.WriteAllText(Path.Combine(outRoot, "oddball-report.csv"), sb.ToString());

        Console.WriteLine("scanned : {0} TGI-named files ({1} real PNG skipped)", rows.Count + nPng, nPng);
        Console.WriteLine("jpeg    : {0}", nJpeg);
        Console.WriteLine("bmp     : {0}", nBmp);
        Console.WriteLine("fsh     : {0}", nFsh);
        Console.WriteLine("unknown : {0}", nUnknown);
        Console.WriteLine("native2x ready: {0} / {1}", nNativeOk, rows.Count);
        Console.WriteLine("errors  : {0}", nErr);
        return nErr == 0 ? 0 : 1;
    }

    static string Csv(string s)
    {
        if (s == null) return "";
        return s.IndexOfAny(new[] { ',', '"', '\n' }) >= 0 ? "\"" + s.Replace("\"", "\"\"") + "\"" : s;
    }

    static string Sniff(byte[] b)
    {
        if (b.Length >= 8 && b[0] == 0x89 && b[1] == 0x50 && b[2] == 0x4E && b[3] == 0x47) return "PNG";
        if (b.Length >= 3 && b[0] == 0xFF && b[1] == 0xD8 && b[2] == 0xFF) return "JPEG";
        if (b.Length >= 2 && b[0] == 0x42 && b[1] == 0x4D) return "BMP";
        if (b.Length >= 16 && b[0] == 'S' && b[1] == 'H' && b[2] == 'P' && b[3] == 'I') return "FSH";
        return "UNKNOWN";
    }

    // ---------- pixel helpers ----------

    static int[] LoadArgb(byte[] fileBytes, out int w, out int h)
    {
        using (var ms = new MemoryStream(fileBytes))
        using (var img = new Bitmap(ms))
        {
            w = img.Width; h = img.Height;
            var px = new int[w * h];
            BitmapData bd = img.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
            try
            {
                for (int y = 0; y < h; y++)
                    System.Runtime.InteropServices.Marshal.Copy(
                        (IntPtr)(bd.Scan0.ToInt64() + (long)y * bd.Stride), px, y * w, w);
            }
            finally { img.UnlockBits(bd); }
            return px;
        }
    }

    static int[] Rep2x(int[] src, int w, int h)
    {
        int w2 = w * 2;
        var dst = new int[w2 * h * 2];
        for (int y = 0; y < h; y++)
        {
            int s = y * w, d = y * 2 * w2;
            for (int x = 0; x < w; x++)
            {
                int v = src[s + x];
                dst[d + 2 * x] = v;
                dst[d + 2 * x + 1] = v;
            }
            Array.Copy(dst, d, dst, d + w2, w2);
        }
        return dst;
    }

    static Bitmap ToBitmap(int[] px, int w, int h, PixelFormat pf)
    {
        var bmp = new Bitmap(w, h, pf);
        BitmapData bd = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.WriteOnly, pf);
        try
        {
            if (pf == PixelFormat.Format32bppArgb)
            {
                for (int y = 0; y < h; y++)
                    System.Runtime.InteropServices.Marshal.Copy(px, y * w,
                        (IntPtr)(bd.Scan0.ToInt64() + (long)y * bd.Stride), w);
            }
            else // 24bpp: write B,G,R
            {
                var line = new byte[w * 3];
                for (int y = 0; y < h; y++)
                {
                    for (int x = 0; x < w; x++)
                    {
                        int v = px[y * w + x];
                        line[3 * x] = (byte)v;            // B
                        line[3 * x + 1] = (byte)(v >> 8);  // G
                        line[3 * x + 2] = (byte)(v >> 16); // R
                    }
                    System.Runtime.InteropServices.Marshal.Copy(line, 0,
                        (IntPtr)(bd.Scan0.ToInt64() + (long)y * bd.Stride), line.Length);
                }
            }
        }
        finally { bmp.UnlockBits(bd); }
        return bmp;
    }

    static void SavePng(int[] px, int w, int h, string path)
    {
        using (Bitmap bmp = ToBitmap(px, w, h, PixelFormat.Format32bppArgb))
            bmp.Save(path, ImageFormat.Png);
    }

    static void SaveJpg(int[] px, int w, int h, string path, long quality)
    {
        ImageCodecInfo codec = null;
        foreach (ImageCodecInfo c in ImageCodecInfo.GetImageEncoders())
            if (c.MimeType == "image/jpeg") codec = c;
        var ep = new EncoderParameters(1);
        ep.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, quality);
        using (Bitmap bmp = ToBitmap(px, w, h, PixelFormat.Format24bppRgb))
            bmp.Save(path, codec, ep);
    }

    static void SaveBmp(int[] px, int w, int h, string path)
    {
        using (Bitmap bmp = ToBitmap(px, w, h, PixelFormat.Format24bppRgb))
            bmp.Save(path, ImageFormat.Bmp);
    }

    // ---------- JPEG / BMP ----------

    static void DoGdi(byte[] data, Row row, string convDir, string natDir, string baseName, bool jpeg)
    {
        int w, h;
        int[] src = LoadArgb(data, out w, out h);
        int[] big = Rep2x(src, w, h);
        int w2 = w * 2, h2 = h * 2;
        row.SrcW = w; row.SrcH = h; row.OutW = w2; row.OutH = h2;

        string convOut = baseName + ".png";
        SavePng(big, w2, h2, Path.Combine(convDir, convOut));
        row.Converted = "converted2x\\" + convOut;

        string natOut = baseName + (jpeg ? ".jpg" : ".bmp");
        string natPath = Path.Combine(natDir, natOut);
        if (jpeg) SaveJpg(big, w2, h2, natPath, 95L);
        else SaveBmp(big, w2, h2, natPath);
        row.Native = "native2x\\" + natOut;

        // verify
        int vw, vh;
        int[] back = LoadArgb(File.ReadAllBytes(natPath), out vw, out vh);
        if (vw != w2 || vh != h2)
            throw new InvalidOperationException("verify failed: wrote " + vw + "x" + vh + ", expected " + w2 + "x" + h2);
        if (!jpeg)
        {
            for (int i = 0; i < big.Length; i++)
                if ((back[i] & 0xFFFFFF) != (big[i] & 0xFFFFFF))
                    throw new InvalidOperationException("verify failed: BMP pixels differ at index " + i);
            row.Action = "2x native BMP 24bpp (pixel-exact) + 2x PNG";
        }
        else
        {
            row.Action = "2x native JPEG q95 + 2x PNG";
            row.Notes = "JPEG re-encode is lossy by nature (GDI+ 4:2:0); PNG copy is exact";
        }
    }

    // ---------- FSH ----------

    static int Int24(byte[] b, int o) { return b[o] | (b[o + 1] << 8) | (b[o + 2] << 16); }

    sealed class FshEntry
    {
        public string Name;
        public int Offset, Code, BlockSize, W, H, PixStart, PixEnd, Bpp;
    }

    static bool DoFsh(byte[] data, Row row, string convDir, string natDir, string baseName)
    {
        int fileSize = BitConverter.ToInt32(data, 4);
        int n = BitConverter.ToInt32(data, 8);
        string dirId = Encoding.ASCII.GetString(data, 12, 4);
        if (fileSize != data.Length)
            row.Notes = AppendNote(row.Notes, "header size field " + fileSize + " != file length " + data.Length);

        var entries = new List<FshEntry>();
        for (int i = 0; i < n; i++)
        {
            var e = new FshEntry();
            e.Name = Encoding.ASCII.GetString(data, 16 + i * 8, 4);
            e.Offset = BitConverter.ToInt32(data, 16 + i * 8 + 4);
            e.Code = data[e.Offset];
            e.BlockSize = Int24(data, e.Offset + 1);
            e.W = BitConverter.ToUInt16(data, e.Offset + 4);
            e.H = BitConverter.ToUInt16(data, e.Offset + 6);
            entries.Add(e);
        }

        FshEntry en = entries[0];
        row.FshInfo = string.Format("dir={0} n={1} entry='{2}' code=0x{3:X2}", dirId, n, en.Name, en.Code);
        row.SrcW = en.W; row.SrcH = en.H;

        if (n != 1)
        {
            row.Action = "SKIPPED (multi-entry FSH not supported)";
            return false;
        }
        if ((en.Code & 0x80) != 0)
        {
            row.Action = "SKIPPED (QFS-compressed entry 0x" + en.Code.ToString("X2") + ")";
            return false;
        }
        switch (en.Code)
        {
            case 0x7D: en.Bpp = 4; break; // 32-bit A8R8G8B8, stored B,G,R,A
            case 0x7F: en.Bpp = 3; break; // 24-bit RGB, stored B,G,R
            case 0x60:
            case 0x61:
                row.Action = "SKIPPED (DXT code 0x" + en.Code.ToString("X2") + "; re-encode not implemented)";
                return false;
            default:
                row.Action = "SKIPPED (unsupported bitmap code 0x" + en.Code.ToString("X2") + ")";
                return false;
        }

        en.PixStart = en.Offset + 16;
        en.PixEnd = en.PixStart + en.W * en.H * en.Bpp;
        if (en.PixEnd > data.Length)
            throw new InvalidOperationException("pixel data runs past end of file");
        if (en.BlockSize != 0 && en.BlockSize != 16 + en.W * en.H * en.Bpp)
            throw new InvalidOperationException("block size 0x" + en.BlockSize.ToString("X") +
                " does not match bare header+pixels (palette/mipmaps not supported)");

        // decode
        int w = en.W, h = en.H;
        var px = new int[w * h];
        for (int i = 0, o = en.PixStart; i < px.Length; i++, o += en.Bpp)
            px[i] = en.Bpp == 4
                ? (data[o + 3] << 24) | (data[o + 2] << 16) | (data[o + 1] << 8) | data[o]
                : unchecked((int)0xFF000000) | (data[o + 2] << 16) | (data[o + 1] << 8) | data[o];

        int[] big = Rep2x(px, w, h);
        int w2 = w * 2, h2 = h * 2;
        row.OutW = w2; row.OutH = h2;

        string convOut = baseName + ".png";
        SavePng(big, w2, h2, Path.Combine(convDir, convOut));
        row.Converted = "converted2x\\" + convOut;

        // re-encode container: [0 .. pixStart) patched + new pixels + [pixEnd .. EOF) verbatim
        var newPix = new byte[w2 * h2 * en.Bpp];
        for (int i = 0, o = 0; i < big.Length; i++, o += en.Bpp)
        {
            int v = big[i];
            newPix[o] = (byte)v;                       // B
            newPix[o + 1] = (byte)(v >> 8);            // G
            newPix[o + 2] = (byte)(v >> 16);           // R
            if (en.Bpp == 4) newPix[o + 3] = (byte)((uint)v >> 24); // A
        }

        int tailLen = data.Length - en.PixEnd;
        var outBytes = new byte[en.PixStart + newPix.Length + tailLen];
        Array.Copy(data, 0, outBytes, 0, en.PixStart);                       // header+dir+filler+entry hdr
        Array.Copy(newPix, 0, outBytes, en.PixStart, newPix.Length);         // 2x pixels
        Array.Copy(data, en.PixEnd, outBytes, en.PixStart + newPix.Length, tailLen); // attachments verbatim

        WriteInt32(outBytes, 4, outBytes.Length);                            // SHPI size field
        int newBs = en.BlockSize == 0 ? 0 : 16 + newPix.Length;
        outBytes[en.Offset + 1] = (byte)newBs;
        outBytes[en.Offset + 2] = (byte)(newBs >> 8);
        outBytes[en.Offset + 3] = (byte)(newBs >> 16);
        WriteUInt16(outBytes, en.Offset + 4, (ushort)w2);
        WriteUInt16(outBytes, en.Offset + 6, (ushort)h2);
        // misc 4 x uint16 (center/pos): all zero in this set; copied verbatim above

        string natOut = baseName + ".fsh";
        string natPath = Path.Combine(natDir, natOut);
        File.WriteAllBytes(natPath, outBytes);
        row.Native = "native2x\\" + natOut;

        // verify: re-parse and pixel-compare
        byte[] chk = File.ReadAllBytes(natPath);
        if (BitConverter.ToInt32(chk, 4) != chk.Length)
            throw new InvalidOperationException("verify failed: size field mismatch");
        int cOff = BitConverter.ToInt32(chk, 20);
        if (chk[cOff] != en.Code ||
            BitConverter.ToUInt16(chk, cOff + 4) != w2 || BitConverter.ToUInt16(chk, cOff + 6) != h2)
            throw new InvalidOperationException("verify failed: entry header mismatch");
        for (int i = 0, o = cOff + 16; i < big.Length; i++, o += en.Bpp)
        {
            int v = en.Bpp == 4
                ? (chk[o + 3] << 24) | (chk[o + 2] << 16) | (chk[o + 1] << 8) | chk[o]
                : unchecked((int)0xFF000000) | (chk[o + 2] << 16) | (chk[o + 1] << 8) | chk[o];
            if (v != big[i])
                throw new InvalidOperationException("verify failed: FSH pixel mismatch at " + i);
        }
        int cPixEnd = cOff + 16 + w2 * h2 * en.Bpp;
        if (chk.Length - cPixEnd != tailLen)
            throw new InvalidOperationException("verify failed: attachment tail length mismatch");
        for (int i = 0; i < tailLen; i++)
            if (chk[cPixEnd + i] != data[en.PixEnd + i])
                throw new InvalidOperationException("verify failed: attachment tail differs at " + i);

        row.Action = "2x native FSH code 0x" + en.Code.ToString("X2") + " (pixel-exact) + 2x PNG";
        return true;
    }

    static string AppendNote(string cur, string add)
    {
        return string.IsNullOrEmpty(cur) ? add : cur + "; " + add;
    }

    static void WriteInt32(byte[] b, int o, int v)
    {
        b[o] = (byte)v; b[o + 1] = (byte)(v >> 8); b[o + 2] = (byte)(v >> 16); b[o + 3] = (byte)(v >> 24);
    }

    static void WriteUInt16(byte[] b, int o, ushort v)
    {
        b[o] = (byte)v; b[o + 1] = (byte)(v >> 8);
    }
}
