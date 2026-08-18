// Upscale2x - batch integer/fractional PNG upscaler for SimCity 4 UI art.
// Usage: Upscale2x.exe <inDir> <outDir> [--factor N] [--hq] [--normalize-names]
//   --factor N   : scale factor. Default 2. Supported: 2, 3 (integer) and 1.5.
//                  Integer factors use exact block-replicate nearest-neighbor.
//                  1.5 uses fractional nearest-neighbor (floor(o/factor) sampling)
//                  - the least-soft resampling; every output pixel is an EXACT
//                  copy of a source pixel, so alpha / colorkey never bleed (the
//                  only artifact is a 2:1 pixel-doubling pattern, no softness).
//   --hq         : System.Drawing HighQualityBicubic (SourceCopy compositing,
//                  PixelOffsetMode.Half, WrapMode.TileFlipXY to avoid edge bleed).
//                  Honors --factor. Softer; NOT used for the shipped packages.
//   --normalize-names : rewrite output filenames matching the SC4 resource pattern
//                  T-<t>_G-<g>_I-<i>.png to the canonical 0x-prefixed lowercase
//                  form T-0x<t8>_G-0x<g8>_I-0x<i8>.png (what the DAT builders
//                  expect). Non-matching names pass through unchanged.
// Output dimensions use round-half-up (floor(dim*factor + 0.5)); the DAT builders
// scale imagerect/area with the SAME rule, so 9-slice insets stay inside the art.
// For integer factors this is exactly dim*N (2x output stays byte-for-byte as before).
// Recurses inDir, mirrors the directory structure into outDir. A file with a .png
// name whose bytes are NOT a real PNG (bad magic) is reported and NOT processed.
// Exit code: 0 = no failures, 1 = one or more failures / bad arguments.

using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;

internal static class Upscale2x
{
    // #156: TGI -> state count, from find_cell_strips.py. Empty unless
    // --cell-strips is passed, so the default build is unchanged.
    private static readonly Dictionary<ulong, int> sCellStrips = new Dictionary<ulong, int>();

    // #157: TGIs PROVEN to be 9-slice frames and never state strips, from
    // find_nine_slice.py. Empty unless --nine-slice is passed, so the default
    // build is unchanged. See CellUnit for what membership does.
    private static readonly HashSet<ulong> sNineSlice = new HashSet<ulong>();

    // #160: TGIs PROVEN to be tiled backgrounds, from find_tiled.py. Empty
    // unless --no-snap is passed. A tiled sheet has NO cell divide at all, so
    // a snap can only desynchronise it from its window. See CellUnit.
    private static readonly HashSet<ulong> sNoSnap = new HashSet<ulong>();
    // #175: sheets whose EXACT PIXEL EDGES are measured by a downstream builder.
    // Smoothing turns a hard edge into a gradient and moves what the measurer
    // finds. See --no-smooth.
    private static readonly HashSet<ulong> sNoSmooth = new HashSet<ulong>();
    private static bool sNoSmoothThis = false;
    private static int sSmoothSkippedMeasured = 0;
    private static int sStripStates;      // per-file, reset every iteration

    private static readonly byte[] PngMagic = { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A };

    private static readonly Regex TgiNameRe = new Regex(
        @"^T-(?:0x)?([0-9A-Fa-f]{1,8})_G-(?:0x)?([0-9A-Fa-f]{1,8})_I-(?:0x)?([0-9A-Fa-f]{1,8})\.png$",
        RegexOptions.IgnoreCase);

    private static int Main(string[] args)
    {
        // ⛔ NEAREST-NEIGHBOUR IS THE DEFAULT AT EVERY FACTOR. DO NOT MAKE --hq
        // AUTOMATIC. THIS HAS NOW BEEN DECIDED TWICE.
        //
        // README.md line 505 has said so since the 2x pipeline was written:
        //     "Nearest-neighbor is the default and the right answer; the HQ
        //      scaler was rejected (blurs pixel art, FRINGES THE MAGENTA
        //      COLORKEY)."
        //
        // 2026-08-06 that was overridden anyway - hq was made automatic for
        // fractional factors on the theory that 1.5's uneven row duplication
        // was causing white streaks on flyout art. It was not, and the
        // rejected option failed in precisely the documented way within one
        // launch: magenta 0xFF00FF is this game's TRANSPARENCY KEY, and any
        // interpolating filter turns an exact key pixel into 0xFE01FE. The
        // key test then misses it and the key colour DRAWS. The user's Mayor
        // Rating bar went pink and pink outlines appeared around the news
        // reader. Both are colour-key art. See _tests/REGRESSION.md #143.
        //
        // ⚠ THE STRUCTURAL POINT THAT SHOULD HAVE STOPPED THIS BEFORE THE
        // BUILD: nearest-neighbour only ever COPIES source pixels. It cannot
        // introduce a colour that is not already in the source. So a WHITE
        // line that is not in the 1x art can never be an NN resampling
        // artifact - which means the upscaler was never a candidate cause and
        // no amount of changing it could have helped. The real cause is
        // draw-time (see the cell-divide note in ScaleDim).
        //
        // --hq remains available for a deliberate side-by-side comparison. It
        // is not safe to ship.
        bool hqExplicit = false;
        bool hq = false;
        bool normalizeNames = false;
        double factor = 2.0;
        var positional = new List<string>();
        for (int ai = 0; ai < args.Length; ai++)
        {
            string a = args[ai];
            if (string.Equals(a, "--hq", StringComparison.OrdinalIgnoreCase)) { hq = true; hqExplicit = true; }
            else if (string.Equals(a, "--nearest", StringComparison.OrdinalIgnoreCase)) { hq = false; hqExplicit = true; }
            else if (string.Equals(a, "--normalize-names", StringComparison.OrdinalIgnoreCase)) normalizeNames = true;
            else if (string.Equals(a, "--height-exact-group", StringComparison.OrdinalIgnoreCase))
            {
                // ⛔ SCOPED BY TGI GROUP ON PURPOSE. A global "never snap the
                // height" moves 791 of the 2280 pristine sheets and puts #143's
                // white-seam fix back in play across the whole game. Naming the
                // group keeps it to the horizontal state-strip families.
                uint grp;
                if (ai + 1 >= args.Length ||
                    !uint.TryParse(args[ai + 1].Replace("0x", "").Replace("0X", ""),
                                   NumberStyles.HexNumber, CultureInfo.InvariantCulture, out grp))
                {
                    Console.Error.WriteLine("--height-exact-group requires a hex TGI group (e.g. 6A386D26)");
                    return Usage();
                }
                sHeightExactGroups.Add(grp);
                ai++;
            }
            else if (string.Equals(a, "--height-exact-strips", StringComparison.OrdinalIgnoreCase))
            {
                // #162: the same derived state-strip list as --cell-strips, but
                // it changes the HEIGHT rule ONLY. Separate flag on purpose -
                // see the note at the sNoHeightSnap assignment.
                if (ai + 1 >= args.Length || !File.Exists(args[ai + 1]))
                {
                    Console.Error.WriteLine("--height-exact-strips requires a readable "
                        + "file (tools\\upscale\\cell-strips.txt)");
                    return Usage();
                }
                foreach (string ln in File.ReadAllLines(args[ai + 1]))
                {
                    string s2 = ln.Trim();
                    if (s2.Length == 0 || s2.StartsWith("#")) { continue; }
                    string[] pp = s2.Split(new[] { ' ', '\t' },
                        StringSplitOptions.RemoveEmptyEntries);
                    if (pp.Length < 2) { continue; }
                    uint g3, i3;
                    if (!uint.TryParse(pp[0], NumberStyles.HexNumber,
                            CultureInfo.InvariantCulture, out g3) ||
                        !uint.TryParse(pp[1], NumberStyles.HexNumber,
                            CultureInfo.InvariantCulture, out i3))
                    {
                        continue;
                    }
                    sHeightExactStrips.Add(((ulong)g3 << 32) | i3);
                }
                Console.Error.WriteLine("height-exact-strips: " + sHeightExactStrips.Count
                    + " sheet(s) will take an EXACT height (no vertical cell snap)");
                ai++;
            }
            else if (string.Equals(a, "--cell-strips", StringComparison.OrdinalIgnoreCase))
            {
                // ⛔ A DERIVED LIST, NOT A HEURISTIC - and that distinction is
                // the whole of #156. Scoping cell-aligned sampling by
                // CellUnit's guess changed 1186 of 2206 sheets and displaced
                // an advisor aperture. This file is produced by
                // find_cell_strips.py from the .UI scripts that actually BIND
                // each sheet, so every entry is a sheet some script draws one
                // state of. 193 sheets, not 1186.
                if (ai + 1 >= args.Length || !File.Exists(args[ai + 1]))
                {
                    Console.Error.WriteLine("--cell-strips requires a readable file "
                                            + "(see find_cell_strips.py)");
                    return Usage();
                }
                foreach (string line in File.ReadAllLines(args[ai + 1]))
                {
                    string s = line.Trim();
                    if (s.Length == 0 || s[0] == '#') continue;
                    string[] parts = s.Split(new[] { ' ', '\t' },
                                             StringSplitOptions.RemoveEmptyEntries);
                    uint g2, i2; int n2;
                    if (parts.Length >= 3
                        && uint.TryParse(parts[0], NumberStyles.HexNumber,
                                         CultureInfo.InvariantCulture, out g2)
                        && uint.TryParse(parts[1], NumberStyles.HexNumber,
                                         CultureInfo.InvariantCulture, out i2)
                        && int.TryParse(parts[2], out n2) && n2 >= 2)
                    {
                        sCellStrips[((ulong)g2 << 32) | i2] = n2;
                    }
                }
                Console.Error.WriteLine("cell-strips: " + sCellStrips.Count
                                        + " sheet(s) will be sampled PER STATE");
                ai++;
            }
            else if (string.Equals(a, "--smooth-unkeyed", StringComparison.OrdinalIgnoreCase))
            {
                // #175. Smooth (Catmull-Rom) resample, but ONLY for sheets with
                // no exact FF00FF anywhere and ONLY at fractional factors. See
                // UpscaleSmoothUnkeyed. This is NOT --hq: it refuses every
                // colour-keyed sheet outright rather than trying to survive one.
                sSmoothUnkeyed = true;
            }
            else if (string.Equals(a, "--smooth-keyed", StringComparison.OrdinalIgnoreCase))
            {
                // #175 SECOND HALF (2026-08-16). Extends --smooth-unkeyed to the
                // 465 sheets that carry the FF00FF key and were being refused.
                //
                // ⛔ THIS IS STILL NOT --hq, AND THE DIFFERENCE IS THE WHOLE
                // POINT. --hq let Graphics.DrawImage average an exact FF00FF with
                // its neighbours; the result was 0xFE01FE, the key test missed
                // it, and the key DREW - that is what turned the Mayor Rating bar
                // pink (#143). Here the key NEVER ENTERS AN AVERAGE: key pixels
                // carry zero coverage, each output pixel divides by the coverage
                // it actually accumulated, and any pixel below half coverage is
                // re-emitted as an EXACT FF00FF. Requires --smooth-unkeyed.
                //
                // WHY IT MATTERS: nearest-neighbour at a fractional factor makes
                // a 3px-wide tick 5px or 4px depending on whether its origin is
                // even or odd, so the HUD Mayor Rating ladder renders its red
                // half bolder than its green half at 1.5x. At 2x NN is an exact
                // block replicate and the same sheet is perfectly crisp - which
                // is exactly the "2x looks way sharper" the user reported.
                sSmoothKeyed = true;
            }
            else if (string.Equals(a, "--nine-slice", StringComparison.OrdinalIgnoreCase))
            {
                // ⛔ ALSO A DERIVED LIST (#157), and for the same reason as
                // --cell-strips: CellUnit's {3,4} guess RESIZES sheets, and
                // "180 divides by 4" is not evidence of four states. Produced by
                // find_nine_slice.py from the .UI scripts that BIND each sheet.
                if (ai + 1 >= args.Length || !File.Exists(args[ai + 1]))
                {
                    Console.Error.WriteLine("--nine-slice requires a readable file "
                                            + "(see find_nine_slice.py)");
                    return Usage();
                }
                foreach (string line in File.ReadAllLines(args[ai + 1]))
                {
                    string s = line.Trim();
                    if (s.Length == 0 || s[0] == '#') continue;
                    string[] parts = s.Split(new[] { ' ', '\t' },
                                             StringSplitOptions.RemoveEmptyEntries);
                    uint g3, i3;
                    if (parts.Length >= 2
                        && uint.TryParse(parts[0], NumberStyles.HexNumber,
                                         CultureInfo.InvariantCulture, out g3)
                        && uint.TryParse(parts[1], NumberStyles.HexNumber,
                                         CultureInfo.InvariantCulture, out i3))
                    {
                        sNineSlice.Add(((ulong)g3 << 32) | i3);
                    }
                }
                Console.Error.WriteLine("nine-slice: " + sNineSlice.Count
                                        + " sheet(s) will be sized with CellUnit {3}");
                ai++;
            }
            else if (string.Equals(a, "--no-smooth", StringComparison.OrdinalIgnoreCase))
            {
                // ⛔ #175 - SHEETS WHOSE EDGES ARE MEASURED, NOT JUST DRAWN.
                // The advisor FRAME sheets are scanned pixel-by-pixel by
                // build_selective_safe.py::seat_faces_on_apertures to locate the
                // aperture the 3D head sits in (#152). Catmull-Rom turns that
                // hard aperture edge into a gradient, the scan lands one pixel
                // in, and the seat guard correctly refuses the build:
                //     FATAL seat 0x0A15C7D8: aperture 71x77 != face 72x78
                // Generated by make_no_smooth.py from ADVISOR_FACE_SEATS, so it
                // tracks the seat table instead of being a hand-list that rots.
                if (ai + 1 >= args.Length || !File.Exists(args[ai + 1]))
                {
                    Console.Error.WriteLine("--no-smooth requires a readable file "
                                            + "(see make_no_smooth.py)");
                    return Usage();
                }
                foreach (string line in File.ReadAllLines(args[ai + 1]))
                {
                    string s2 = line.Trim();
                    if (s2.Length == 0 || s2[0] == '#') continue;
                    string[] p2 = s2.Split(new[] { ' ', '	' },
                                           StringSplitOptions.RemoveEmptyEntries);
                    uint g5, i5;
                    if (p2.Length >= 2
                        && uint.TryParse(p2[0], NumberStyles.HexNumber,
                                         CultureInfo.InvariantCulture, out g5)
                        && uint.TryParse(p2[1], NumberStyles.HexNumber,
                                         CultureInfo.InvariantCulture, out i5))
                    {
                        sNoSmooth.Add(((ulong)g5 << 32) | i5);
                    }
                }
                Console.Error.WriteLine("no-smooth: " + sNoSmooth.Count
                    + " sheet(s) keep NEAREST (their edges are measured downstream)");
                ai++;
            }
            else if (string.Equals(a, "--no-snap", StringComparison.OrdinalIgnoreCase))
            {
                // ⛔ THE THIRD DERIVED LIST (#160). A blttype=tiled background
                // has NO cell divide to preserve - the engine repeats the source
                // across the destination, so the ONLY thing that matters is that
                // the scaled sheet still equals the scaled WINDOW. Snapping it
                // does the one thing that cannot help and can hurt. Produced by
                // find_tiled.py.
                if (ai + 1 >= args.Length || !File.Exists(args[ai + 1]))
                {
                    Console.Error.WriteLine("--no-snap requires a readable file "
                                            + "(see find_tiled.py)");
                    return Usage();
                }
                foreach (string line in File.ReadAllLines(args[ai + 1]))
                {
                    string s = line.Trim();
                    if (s.Length == 0 || s[0] == '#') continue;
                    string[] parts = s.Split(new[] { ' ', '\t' },
                                             StringSplitOptions.RemoveEmptyEntries);
                    uint g4, i4;
                    if (parts.Length >= 2
                        && uint.TryParse(parts[0], NumberStyles.HexNumber,
                                         CultureInfo.InvariantCulture, out g4)
                        && uint.TryParse(parts[1], NumberStyles.HexNumber,
                                         CultureInfo.InvariantCulture, out i4))
                    {
                        sNoSnap.Add(((ulong)g4 << 32) | i4);
                    }
                }
                Console.Error.WriteLine("no-snap: " + sNoSnap.Count
                                        + " tiled sheet(s) will be sized with NO snap");
                ai++;
            }
            else if (string.Equals(a, "--factor", StringComparison.OrdinalIgnoreCase))
            {
                if (ai + 1 >= args.Length ||
                    !double.TryParse(args[ai + 1], NumberStyles.Float, CultureInfo.InvariantCulture, out factor))
                {
                    Console.Error.WriteLine("--factor requires a numeric value (e.g. 1.5, 2, 3)");
                    return Usage();
                }
                ai++;
            }
            else if (a.StartsWith("--", StringComparison.Ordinal))
            {
                Console.Error.WriteLine("Unknown option: " + a);
                return Usage();
            }
            else positional.Add(a);
        }
        // ⛔ THERE IS NO FACTOR-DERIVED DEFAULT. hq stays false unless the
        // caller passes --hq explicitly. See the block above: interpolation
        // fringes the magenta colour key at EVERY factor, so there is no
        // factor for which turning it on automatically is correct.
        //
        // (2026-08-06: the auto-hq line was first "reverted" by rewriting only
        // the comment above it. The tool went on printing "Mode: high-quality"
        // and regenerated the whole 1.5x tier bicubic AGAIN. The printed Mode
        // line is the only reason that was caught - INSTALLED IS NOT EXECUTED,
        // and a comment is not code.)
        if (hqExplicit && hq)
            Console.Error.WriteLine("WARNING: --hq fringes the magenta colour key; " +
                                    "for comparison only, do not ship this output.");
        if (positional.Count != 2) return Usage();
        if (!(factor > 1.0) || factor > 16.0)
        {
            Console.Error.WriteLine("--factor must be in (1.0, 16.0]; got " + factor.ToString(CultureInfo.InvariantCulture));
            return 1;
        }

        string inDir = Path.GetFullPath(positional[0]);
        string outDir = Path.GetFullPath(positional[1]);
        if (!Directory.Exists(inDir))
        {
            Console.Error.WriteLine("Input directory not found: " + inDir);
            return 1;
        }
        if (string.Equals(inDir.TrimEnd('\\'), outDir.TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
        {
            Console.Error.WriteLine("Input and output directories must differ.");
            return 1;
        }

        int processed = 0, skippedExt = 0, badMagic = 0;
        var failures = new List<string>();
        var badMagicFiles = new List<string>();
        string inRoot = inDir.TrimEnd('\\') + "\\";

        foreach (string path in Directory.GetFiles(inDir, "*", SearchOption.AllDirectories))
        {
            if (!string.Equals(Path.GetExtension(path), ".png", StringComparison.OrdinalIgnoreCase))
            {
                skippedExt++;
                continue;
            }

            string rel = Path.GetFullPath(path).Substring(inRoot.Length);
            // Per-file: does this sheet's TGI group take its height exactly?
            // (see --height-exact-group). Reset every iteration so one matching
            // file cannot leak the flag onto the next one.
            // Reset every iteration for the same reason sNoHeightSnap is:
            // one matching file must never leak its mode onto the next.
            sStripStates = 0;
            if (sCellStrips.Count > 0)
            {
                Match sm = TgiNameRe.Match(Path.GetFileName(rel));
                if (sm.Success)
                {
                    ulong key = ((ulong)Convert.ToUInt32(sm.Groups[2].Value, 16) << 32)
                                | Convert.ToUInt32(sm.Groups[3].Value, 16);
                    int n;
                    if (sCellStrips.TryGetValue(key, out n)) sStripStates = n;
                }
            }
            // Same per-file reset discipline as sNoHeightSnap below: one
            // matching file must never leak its mode onto the next.
            // #160, same per-file reset discipline as the flags around it.
            sNoSmoothThis = false;
            if (sNoSmooth.Count > 0)
            {
                Match nm = TgiNameRe.Match(Path.GetFileName(rel));
                if (nm.Success)
                {
                    ulong nkey = ((ulong)Convert.ToUInt32(nm.Groups[2].Value, 16) << 32)
                                 | Convert.ToUInt32(nm.Groups[3].Value, 16);
                    sNoSmoothThis = sNoSmooth.Contains(nkey);
                }
            }
            sNoSnapThis = false;
            if (sNoSnap.Count > 0)
            {
                Match tm = TgiNameRe.Match(Path.GetFileName(rel));
                if (tm.Success)
                {
                    ulong tkey = ((ulong)Convert.ToUInt32(tm.Groups[2].Value, 16) << 32)
                                 | Convert.ToUInt32(tm.Groups[3].Value, 16);
                    sNoSnapThis = sNoSnap.Contains(tkey);
                }
            }
            sNineSliceOnly = false;
            if (sNineSlice.Count > 0)
            {
                Match nm = TgiNameRe.Match(Path.GetFileName(rel));
                if (nm.Success)
                {
                    ulong nkey = ((ulong)Convert.ToUInt32(nm.Groups[2].Value, 16) << 32)
                                 | Convert.ToUInt32(nm.Groups[3].Value, 16);
                    sNineSliceOnly = sNineSlice.Contains(nkey);
                }
            }
            sNoHeightSnap = false;
            if (sHeightExactGroups.Count > 0)
            {
                Match gm = TgiNameRe.Match(Path.GetFileName(rel));
                if (gm.Success &&
                    sHeightExactGroups.Contains(Convert.ToUInt32(gm.Groups[2].Value, 16)))
                {
                    sNoHeightSnap = true;
                }
            }
            // ⛔ #162: EVERY DERIVED STATE STRIP IS HEIGHT-EXACT, NOT JUST THE
            // GROUPS SOMEONE HAPPENED TO LIST.
            //
            // --height-exact-group above takes a hand-written set of GROUP ids
            // (0x6A386D26 and friends, added for #150). That was always the
            // right RULE applied to the wrong SCOPE: the reason a strip's
            // height must not be snapped is that a horizontal N-state strip is
            // cut horizontally and HAS NO VERTICAL CELL DIVIDE - which is true
            // of every strip in the corpus, not of four groups. Scoping a
            // structural fact to a hand-list is the failure law 86 describes:
            // the sheet's ROLE decides its sizing rule, and `cell-strips.txt`
            // is the DERIVED answer to what that role is (#156).
            //
            // WHAT IT COST while it was hand-scoped. `gate_btn_undercover.py`
            // has been reporting the survivors for weeks as a "known residual,
            // reported not failed": at 1.5x, 347 buttons whose art CELL is
            // taller than its WINDOW, and 0 at 2x and 3x. Measured over the
            // derived list: 32 of 193 strips are snapped at 1.5x, none at 2x or
            // 3x. Three of them are the dashboard's own left-cluster buttons -
            //   {46a006b0,13d14c60/c70/c80}  1x h=21 -> exact 32 -> snapped 33
            //   {46a006b0,13e14f80/91/a0}    1x h=36 -> exact 54 -> snapped 60
            // and the gate independently prints `win 29x32  cell 29x33` for
            // Rotate CW/CCW and Zoom In, which is the same +1 seen from the
            // window side. A sheet taller than its window re-registers every
            // feature inside it vertically: the picture sits low and the band
            // it vacates reads as the bright hairline the user reported under
            // the mayor's hat and the people button (#150's own words: "the
            // picture sat low with a light band above it").
            //
            // ⚠ THIS IS NOT THE GLOBAL DEFAULT THE COMMENT AT sNoHeightSnap
            // WARNS AGAINST. That warning is about dropping the height snap for
            // ALL 2280 sheets, which moves 791 of them and reopens #143. This
            // is scoped to the 193 sheets a .UI proves are state strips, and
            // #143's cure - the WIDTH divide by N - is untouched.
            //
            // ⚠ NO-OP AT AN INTEGER FACTOR, and that is arithmetic rather than
            // hope: ScaleDim returns before CellUnit is consulted when the
            // factor is whole, so 2x and 3x come out byte-identical and the
            // rebuild must hash-match. Assert it, do not argue it.
            // ⚠ ITS OWN FLAG, NOT --cell-strips, AND THAT IS DELIBERATE.
            // --cell-strips ALSO switches on #156's per-state horizontal
            // sampling. Riding this change in on that flag would change two
            // things at 1.5x in one build, and after six missed fixes on this
            // defect a result that cannot be attributed is worth nothing.
            // --height-exact-strips carries the same derived list and changes
            // the HEIGHT rule only.
            if (sHeightExactStrips.Count > 0)
            {
                Match hm = TgiNameRe.Match(Path.GetFileName(rel));
                if (hm.Success)
                {
                    ulong hkey = ((ulong)Convert.ToUInt32(hm.Groups[2].Value, 16) << 32)
                                 | Convert.ToUInt32(hm.Groups[3].Value, 16);
                    if (sHeightExactStrips.Contains(hkey)) { sNoHeightSnap = true; }
                }
            }
            try
            {
                byte[] data = File.ReadAllBytes(path);
                if (!HasPngMagic(data))
                {
                    badMagic++;
                    badMagicFiles.Add(rel);
                    continue;
                }

                string outRel = rel;
                if (normalizeNames)
                {
                    string dirPart = Path.GetDirectoryName(rel);
                    string namePart = Path.GetFileName(rel);
                    Match mm = TgiNameRe.Match(namePart);
                    if (mm.Success)
                    {
                        uint t = Convert.ToUInt32(mm.Groups[1].Value, 16);
                        uint g = Convert.ToUInt32(mm.Groups[2].Value, 16);
                        uint iid = Convert.ToUInt32(mm.Groups[3].Value, 16);
                        string canon = string.Format("T-0x{0:x8}_G-0x{1:x8}_I-0x{2:x8}.png", t, g, iid);
                        outRel = string.IsNullOrEmpty(dirPart) ? canon : Path.Combine(dirPart, canon);
                    }
                }
                string outPath = Path.Combine(outDir, outRel);
                Directory.CreateDirectory(Path.GetDirectoryName(outPath));

                using (var ms = new MemoryStream(data))
                using (var loaded = new Bitmap(ms))
                using (Bitmap src = NormalizeTo32bppArgb(loaded))
                {
                    // #175 dispatch. Three outcomes, each COUNTED - a pass that
                    // reports only what it did lets a silent skip read as
                    // coverage.
                    bool smoothThis = false, keyedThis = false;
                    if (sSmoothUnkeyed && !hq)
                    {
                        if (factor == Math.Floor(factor)) { sSmoothSkippedInteger++; }
                        else if (sNoSmoothThis) { sSmoothSkippedMeasured++; }
                        else if (HasExactColorKey(src))
                        {
                            // #175 second half: a keyed sheet is no longer an
                            // automatic refusal. With --smooth-keyed the key is
                            // excluded from every average and re-applied by
                            // coverage, so it can be smoothed safely.
                            // Fine 1-2px key STRUCTURE cannot survive any
                            // resample - see MinKeyRun. Those keep NEAREST.
                            if (sSmoothKeyed && MinKeyRun(src) >= 3)
                            {
                                smoothThis = true; keyedThis = true; sSmoothedKeyed++;
                            }
                            else if (sSmoothKeyed) { sSmoothSkippedFineKey++; }
                            else { sSmoothSkippedKeyed++; }
                        }
                        else { smoothThis = true; sSmoothed++; }
                    }
                    using (Bitmap dst = hq ? UpscaleHq(src, factor)
                                           : (smoothThis ? UpscaleSmoothUnkeyed(src, factor, keyedThis)
                                                         : UpscaleNearest(src, factor)))
                    using (var outMs = new MemoryStream())
                    {
                        dst.Save(outMs, ImageFormat.Png);
                        File.WriteAllBytes(outPath, outMs.ToArray());
                    }
                }
                processed++;
            }
            catch (Exception ex)
            {
                failures.Add(rel + " -> " + ex.Message);
            }
        }

        Console.WriteLine("Factor      : " + factor.ToString(CultureInfo.InvariantCulture) +
                          (normalizeNames ? "  (names normalized to canonical 0x form)" : ""));
        Console.WriteLine("Mode        : " + (hq ? "high-quality (HighQualityBicubic)" : "nearest-neighbor (default)"));
        if (sSmoothUnkeyed)
        {
            // ⚠ REPORT THE REFUSALS, NOT JUST THE WORK. A pass that prints only
            // what it did lets a silent skip read as coverage.
            Console.WriteLine("smooth-unkeyed: " + sSmoothed + " sheet(s) Catmull-Rom resampled; "
                + sSmoothSkippedKeyed + " refused (contain the FF00FF colour key); "
                + sSmoothSkippedMeasured + " refused (edges measured downstream); "
                + sSmoothSkippedInteger + " refused (integer factor - nearest is already exact)");
            Console.WriteLine("smooth-keyed  : " + sSmoothedKeyed + " KEYED sheet(s) resampled with the key excluded; "
                + sSmoothSkippedFineKey + " refused (key is 1-2px STRUCTURE, not a region - nearest preserves it better)"
                + (sSmoothKeyed ? "" : "  [--smooth-keyed not passed; keyed sheets stay NEAREST]"));
        }
        // #171/#165 CELL-FIRST. Reported at EVERY factor, including the integer
        // tiers where the correct answer is a hard zero - see the assertion.
        Console.WriteLine("cell-first  : " + sCellFirst + " strip width(s) sized states*R(cell,f)"
            + (sCellFirstConflict > 0
                ? "; " + sCellFirstConflict + " left on the no-snap rule (in BOTH lists - see below)"
                : ""));
        if (sCellFirstConflict > 0)
        {
            // Not fatal - no-snap is the safer of the two contracts - but it must
            // never be silent, because one sheet cannot honour both rules.
            Console.WriteLine("  WARN      " + sCellFirstConflict + " sheet(s) are in cell-strips.txt AND no-snap.txt."
                + " A sheet cannot both equal its window and divide into N cells."
                + " Decide which it is and remove it from the other list.");
        }
        // ⛔ THE MANDATORY INTEGER CONTROL (law 95). ScaleDim returns before the
        // cell-first branch at an integer factor, so this counter is zero there
        // BY CONSTRUCTION. If it is ever non-zero, the early return moved and the
        // 2x/3x packages are no longer provably byte-identical - which is exactly
        // the regression this rule promises it cannot cause. Fail the build.
        if (factor == Math.Floor(factor) && sCellFirst != 0)
        {
            Console.WriteLine("FATAL: cell-first fired " + sCellFirst + " time(s) at integer factor "
                + factor + ". It must be a provable no-op there (R(c*k)*n == R(c*n*k)).");
            return 1;
        }
        Console.WriteLine("Input       : " + inDir);
        Console.WriteLine("Output      : " + outDir);
        Console.WriteLine("Processed   : " + processed);
        Console.WriteLine("Skipped     : " + skippedExt + " (non-.png extension)");
        Console.WriteLine("Bad magic   : " + badMagic + " (.png name but not PNG data - NOT processed)");
        foreach (string f in badMagicFiles) Console.WriteLine("  BADMAGIC  " + f);
        Console.WriteLine("Failed      : " + failures.Count);
        foreach (string f in failures) Console.WriteLine("  FAIL      " + f);
        return failures.Count == 0 ? 0 : 1;
    }

    private static int Usage()
    {
        Console.Error.WriteLine("Usage: Upscale2x.exe <inDir> <outDir> [--factor N] [--hq] [--normalize-names]");
        Console.Error.WriteLine("  Recursively upscales every PNG under inDir by N (default 2) into outDir");
        Console.Error.WriteLine("  (mirrored structure). The RESAMPLER IS CHOSEN BY THE FACTOR:");
        Console.Error.WriteLine("    integer N    -> nearest-neighbour, an exact NxN block replicate.");
        Console.Error.WriteLine("    fractional N -> high quality, because nearest is NOT exact there:");
        Console.Error.WriteLine("                    at 1.5 it duplicates rows 2,1,2,1 and streaks photos.");
        Console.Error.WriteLine("  --hq / --nearest force the choice either way (both honour --factor).");
        Console.Error.WriteLine("  --normalize-names = rewrite SC4 T-/G-/I- filenames to canonical 0x form.");
        Console.Error.WriteLine("  --height-exact-group <hex> = for that TGI GROUP, snap the WIDTH to the cell");
        Console.Error.WriteLine("                      divide but take the HEIGHT exactly. Horizontal 4-state");
        Console.Error.WriteLine("                      strips have no vertical divide. Repeatable.");
        return 1;
    }

    private static bool HasPngMagic(byte[] data)
    {
        if (data.Length < PngMagic.Length) return false;
        for (int i = 0; i < PngMagic.Length; i++)
            if (data[i] != PngMagic[i]) return false;
        return true;
    }

    // Convert any loaded PNG (indexed 1/4/8bpp, gray, 24bpp, 32bpp...) to
    // non-premultiplied 32bppArgb WITHOUT altering pixel values.
    // Indexed formats are expanded manually via the palette (exact, including
    // per-entry alpha from tRNS); 32bppArgb is raw-copied; everything else goes
    // through a SourceCopy same-size draw (pixel-exact format conversion).
    private static Bitmap NormalizeTo32bppArgb(Bitmap loaded)
    {
        int w = loaded.Width, h = loaded.Height;
        var result = new Bitmap(w, h, PixelFormat.Format32bppArgb);

        switch (loaded.PixelFormat)
        {
            case PixelFormat.Format32bppArgb:
                CopyRaw32(loaded, result);
                break;
            case PixelFormat.Format1bppIndexed:
            case PixelFormat.Format4bppIndexed:
            case PixelFormat.Format8bppIndexed:
                ExpandIndexed(loaded, result);
                break;
            default:
                using (var g = Graphics.FromImage(result))
                {
                    g.CompositingMode = CompositingMode.SourceCopy;
                    g.InterpolationMode = InterpolationMode.NearestNeighbor;
                    g.PixelOffsetMode = PixelOffsetMode.Half;
                    g.DrawImage(loaded, new Rectangle(0, 0, w, h), 0, 0, w, h, GraphicsUnit.Pixel);
                }
                break;
        }
        return result;
    }

    private static void CopyRaw32(Bitmap src, Bitmap dst)
    {
        int w = src.Width, h = src.Height;
        var rect = new Rectangle(0, 0, w, h);
        BitmapData sd = src.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        BitmapData dd = dst.LockBits(rect, ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
        try
        {
            var row = new int[w];
            for (int y = 0; y < h; y++)
            {
                Marshal.Copy(Ofs(sd.Scan0, (long)y * sd.Stride), row, 0, w);
                Marshal.Copy(row, 0, Ofs(dd.Scan0, (long)y * dd.Stride), w);
            }
        }
        finally
        {
            src.UnlockBits(sd);
            dst.UnlockBits(dd);
        }
    }

    private static void ExpandIndexed(Bitmap src, Bitmap dst)
    {
        int w = src.Width, h = src.Height;
        Color[] pal = src.Palette.Entries;
        var palArgb = new int[pal.Length];
        for (int i = 0; i < pal.Length; i++) palArgb[i] = pal[i].ToArgb();

        var rect = new Rectangle(0, 0, w, h);
        BitmapData sd = src.LockBits(rect, ImageLockMode.ReadOnly, src.PixelFormat);
        BitmapData dd = dst.LockBits(rect, ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
        try
        {
            int bpp = (src.PixelFormat == PixelFormat.Format8bppIndexed) ? 8
                    : (src.PixelFormat == PixelFormat.Format4bppIndexed) ? 4 : 1;
            var srow = new byte[sd.Stride];
            var drow = new int[w];
            for (int y = 0; y < h; y++)
            {
                Marshal.Copy(Ofs(sd.Scan0, (long)y * sd.Stride), srow, 0, sd.Stride);
                for (int x = 0; x < w; x++)
                {
                    int idx;
                    if (bpp == 8) idx = srow[x];
                    else if (bpp == 4) idx = (x % 2 == 0) ? (srow[x / 2] >> 4) : (srow[x / 2] & 0x0F);
                    else idx = (srow[x / 8] >> (7 - (x % 8))) & 1;
                    drow[x] = palArgb[idx];
                }
                Marshal.Copy(drow, 0, Ofs(dd.Scan0, (long)y * dd.Stride), w);
            }
        }
        finally
        {
            src.UnlockBits(sd);
            dst.UnlockBits(dd);
        }
    }

    // THE GAME CUTS ART SHEETS INTO CELLS WITH AN INTEGER DIVIDE, AND THE
    // DIVISOR IS BAKED INTO ITS OWN CODE. Two cuts matter:
    //     NineSlice          cell = (img->Width()/3, img->Height()/3)
    //                        (cSC4WinAlertBorder slot-88 draw, VA 0x00794100)
    //     four-state strip   cell = width/4   (normal/hover/pressed/disabled)
    //
    // If the SCALED dimension stops being divisible by that count, cell*count
    // no longer covers the sheet. A 516px four-state strip scaled by 1.5 is
    // 774; the game computes cell = 774/4 = 193 and 4*193 = 772, so the true
    // cell boundary (193.5) drifts half a pixel further out of step in every
    // cell and each state draws a sliver of the NEXT state. The next state is
    // the bright hover art - which is the WHITE SEAM the user reported on the
    // flyout thumbnails, 2026-08-06.
    //
    // ⛔ WHY THIS IS 1.5x-ONLY, AND WHY 2x/3x COULD NEVER HAVE CAUGHT IT:
    // an INTEGER factor preserves divisibility automatically (if N | v then
    // N | k*v for integer k). MEASURED over the 2,206 extracted sources:
    //     factor 1.5 -> 31.0% of /3-eligible and 42.9% of /4-eligible
    //                   dimensions lose divisibility
    //     factor 2.0 -> 0.0%      factor 3.0 -> 0.0%
    // The defect is structurally impossible at every tier that was tested.
    // (Fourth instance of this shape today. See _tests/REGRESSION.md #143.)
    //
    // FIX: at a fractional factor, snap the output to preserve whatever cell
    // divisibility the SOURCE had. That is a rule, not an inventory - it needs
    // no per-TGI table and so cannot silently miss a sheet. The adjustment is
    // bounded by k/2, i.e. at most 6px and usually 0-2.
    //
    // ⚠ INTEGER FACTORS ARE RETURNED UNTOUCHED, so 2x and 3x output stays
    // BYTE-IDENTICAL. That is the safety property; verify it, don't assume it.
    //
    // ⚠ This no longer always equals the builders' scale_len(). It does not
    // need to: build_selective_safe.py::clamp_rect_to_art reads the REAL PNG
    // header (png_wh) and clamps imagerect to the art that actually exists,
    // logging every clamp. Over-read is the failure it already guards.
    // EVERY CELL COUNT THIS GAME IS MEASURED TO USE. Each one is a divide the
    // game performs on the ART's own width or height, with the divisor
    // compiled in:
    //   2  two-state strips        (terraform flyout 0xCA35CBED,
    //                               _vanilla-reference\FINDINGS.md:43)
    //   3  NineSlice, both axes    (cSC4WinAlertBorder draw, VA 0x00794100)
    //   4  four-state button strip (normal/hover/pressed/disabled - GZWinBtn)
    //   8  eight-state strip       (Audio playlist checkbox {14416244},
    //                               384x48 = 8 states of 48, REGRESSION.md:5974)
    //  12  scrollbar art           (cGZWinScrollbar::SetImage 0x9C45F0 sizes the
    //                               bar from art width / 12, REGRESSION.md:2701)
    //   6, 16, 24 are included as plausible siblings; they cost nothing when
    //   they do not divide the source, and the proportionality guard below
    //   stops them from wrecking a small icon that merely happens to divide.
    // ⛔ THE SET IS {3,4}, AND IT WAS MEASURED. DO NOT WIDEN IT.
    //
    // These are the counts the game ACTUALLY cell-divides by in the paths that
    // matter: NineSlice borders take img->Width()/3 (VA 0x00794100) and a
    // button state strip takes width/4. /12 still falls out on its own for the
    // scrollbar (cGZWinScrollbar::SetImage, art width / 12), because a sheet
    // divisible by both 3 and 4 gets LCM = 12 from this very list.
    //
    // ⚠ IT USED TO BE {2,3,4,6,8,12,16,24} AND THAT WAS A BUG WITH A
    // PLAUSIBLE STORY. The reasoning was "take the LCM of every count that
    // divides the width, then any divide is safe". It is not safe, it is
    // OVERSHOOT: a 200px FOUR-state sheet (cell 50) has CellUnit = LCM(2,4,8)
    // = 8, so 200*1.5 = 300 - ALREADY a clean multiple of 4 - got pushed to
    // 304 and every cell came out a pixel too wide. The 8 came from 200
    // happening to divide by 8, NOT from the sheet having 8 states.
    //
    // USER-VISIBLE COST (2026-08-06): "Select A My Sim" faces, the advisor
    // portraits, the Monthly Budget rows and the flyout thumbnails all sat
    // slightly wrong in their frames, because their art was a pixel wider than
    // the window drawing it.
    //
    // MEASURED over the 255 art-sized 4-state buttons, counting cell != window:
    //     LCM{2,3,4,6,8,12,16,24}   152   <- what shipped, and the worst
    //     LCM{2,3,4}                 98      option except doing nothing
    //     LCM{3,4}                   34   <- THIS
    //     {4} alone                  19      (rejected: drops NineSlice /3)
    //     no snap at all            104
    //
    // 34 remain. They need the sheet sized from its CONSUMER's window
    // (states * ScaleRound(w,f)), which this tool cannot know - it runs over a
    // directory and never sees a .UI. Doing it in the builder was tried and
    // reverted: art is bound BY TGI, and some consumers are created at runtime
    // and appear in no .UI at all. See _tests\REGRESSION.md #148.
    private static readonly int[] kCellCounts = { 3, 4 };

    private static int Gcd(int a, int b) { while (b != 0) { int t = a % b; a = b; b = t; } return a; }

    // ⛔ THE UNIT IS THE LCM OF EVERY COUNT THAT DIVIDES v, NOT THE FIRST ONE.
    // The first version returned the first match of 12/4/3, which silently
    // under-protected any sheet cut by a count it checked later or not at all.
    // Worked example that shipped broken: an 8-state strip 88px wide takes
    // k=4 (88%4==0), 88*1.5 = 132 is already a multiple of 4, so NO snap fires
    // - but 132/8 = 16.5 and every state still mis-cuts. lcm gives k=8 there
    // and the snap lands on 136. USER-REPORTED 2026-08-06: "#143 isn't fixed
    // 100%, you need to do a deeper scan." They were right.
    // ⛔ CELL-ALIGNED SAMPLING (#156). USER-REPORTED: three bright slivers at
    // the right-hand end of the region bubble's three population rows, at 1.5x
    // only - clean at stock AND clean at 2x, both confirmed on screen.
    //
    // The cause is the two halves of this file disagreeing. ScaleDim snaps the
    // SHEET so its cell count still divides evenly (#143, correct and staying).
    // The SAMPLER then mapped the whole sheet globally, `sx = ox / factor`. As
    // soon as the snap moves the output width off `w * factor`, those two
    // stop agreeing and the CELL BOUNDARIES DRIFT APART:
    //
    //     1x   sheet  84 wide, cell 21   states at 0 / 21 / 42 / 63
    //                                    ink begins exactly at 42 (state 2)
    //     1.5x sheet 132 wide, cell 33   states at 0 / 33 / 66 / 99
    //          out x=63 -> src 42  |
    //          out x=64 -> src 42  |  state 2's ink, drawn INSIDE state 1
    //          out x=65 -> src 43  |
    //
    // Three columns of the NEXT state bleed into the previous state's cell,
    // hard against its right edge - which is the sliver, once per row.
    //
    // The cure is not to touch the snap. It is to scale each cell FROM ITS OWN
    // CELL, so no state's pixels can cross a boundary. Scoped deliberately to
    // sheets the snap actually moved: an unsnapped sheet keeps the exact map it
    // had, so its output is byte-identical and the blast radius is only the
    // sheets that carry the defect.
    //
    // ⚠ PROVABLE NO-OP AT AN INTEGER FACTOR. There ScaleDim returns before
    // CellUnit is consulted, so `snapped` is false and this never engages -
    // and even if it did, blockOut == blockSrc * factor exactly, making the
    // per-block ratio map identical to the factor map. 2x and 3x must come out
    // byte-identical, and the build asserts it.
    //
    // ⚠ NOT the #151 mistake. That was a GLOBAL size-ratio map, which re-timed
    // every sheet's contents against itself. This is a ratio map WITHIN one
    // cell, which is the only frame in which a cell's contents are defined.
    private static int[] BuildSampleMap(int src, int outLen, double factor, int states)
    {
        var map = new int[outLen];
        // factor < 0 marks "height snap suppressed" (--height-exact-group):
        // there is no cell divide on that axis, so never block it.
        // ⛔ THE SCOPE IS THE FIX. `states` comes from find_cell_strips.py,
        // which reads the .UI that BINDS this sheet - so it is 0 for every
        // sheet nobody proved is a strip, and those keep the exact map they
        // have today. Scoping this by CellUnit's guess instead moved 1186 of
        // 2206 sheets and displaced an advisor aperture (#156).
        int k = states;
        if (k > 1 && src % k == 0 && outLen % k == 0)
        {
            int bs = src / k, bo = outLen / k;
            for (int b = 0; b < k; b++)
            {
                for (int i = 0; i < bo; i++)
                {
                    int sx = b * bs + (int)((long)i * bs / bo);
                    if (sx >= (b + 1) * bs) sx = (b + 1) * bs - 1;
                    map[b * bo + i] = sx;
                }
            }
            return map;
        }
        double f = factor > 0 ? factor : (double)outLen / src;
        bool factorMap = outLen >= (long)Math.Floor(src * f);
        for (int o = 0; o < outLen; o++)
        {
            int sx = factorMap ? (int)(o / f) : (int)((long)o * src / outLen);
            if (sx >= src) sx = src - 1;
            map[o] = sx;
        }
        return map;
    }

    // ⛔ A 9-SLICE FRAME HAS ONE CELL COUNT AND IT IS THREE (#157).
    //
    // Set per file from --nine-slice (find_nine_slice.py). When true CellUnit
    // consults {3} alone, because the /4 in kCellCounts is not a property of
    // these sheets - it is the arithmetic accident that their width divides by
    // 4. The two counts want different sizes and taking the LCM satisfies
    // NEITHER:
    //
    //     180x180 frame at 1.5   /3 -> 270   /4 -> 272   LCM 12 -> 276
    //
    // The engine's NineSlice cell is img->Width()/3 (VA 0x00794100). At 276 it
    // is 92 while every geometry number in the .UI was scaled for 90, so the
    // corner art overshoots and the rounded corner never reaches the window
    // corner. USER-REPORTED on the Reconcile Edges dialog: "look how the light
    // blue interior box is overlapping". 418 uncovered px at 1.5x, 4 at 270.
    //
    // ⚠ NO-OP AT AN INTEGER FACTOR, like every other snap here: ScaleDim
    // returns before CellUnit is consulted, so 2x and 3x are byte-identical and
    // the build asserts it. 6 of 30 listed sheets actually move at 1.5x.
    private static bool sNineSliceOnly = false;         // set PER FILE, above
    private static readonly int[] kNineSliceCounts = { 3 };

    // ⛔ A TILED BACKGROUND HAS NO CELL DIVIDE AT ALL (#160). Set per file from
    // --no-snap (find_tiled.py). `blttype=tiled` is src-follows-dst: the engine
    // repeats the source across the destination, so the sheet's ONLY contract
    // is with its WINDOW, and the window scales by a plain round. Snapping the
    // sheet therefore cannot protect anything and CAN desynchronise the pair:
    //
    //   god toolbar rail {46a006b0,14415876}, 1x art 74x351 == window 74x351
    //     1x    art 74x351   window 74x351    delta 0
    //     2x    art 148x702  window 148x702   delta 0     <- integer, snap is a no-op
    //     1.5x  art 111x528  window 111x527   delta +1    <- CellUnit(351)=3 snapped
    //
    // USER-REPORTED as "a break in the white line on the left that is not in 2x
    // or stock". Four sheets across the corpus were desynchronised this way,
    // every one of them at 1.5x only.
    private static bool sNoSnapThis = false;            // set PER FILE, above

    private static int CellUnit(int v)
    {
        if (sNoSnapThis) { return 1; }                   // no divide to preserve
        int k = 1;
        foreach (int n in (sNineSliceOnly ? kNineSliceCounts : kCellCounts))
        {
            if (v % n == 0) { k = k / Gcd(k, n) * n; }   // lcm
        }
        return k;
    }

    // ⛔ A FOUR-STATE STRIP IS CUT HORIZONTALLY. IT HAS NO VERTICAL CELL DIVIDE.
    //
    // When true, ScaleDim's cell snap is applied to the WIDTH only and the
    // height is plain RoundHalfUp. Set by --no-height-snap, and used by the
    // icon builders whose source sets are entirely horizontal state strips
    // (group 0x6A386D26 and friends).
    //
    // WHY IT EXISTS (#150, 2026-08-06). The disaster flyout thumbnails ship
    // 176x44 sheets. At 1.5x the width is exact (176*1.5 = 264, a clean
    // multiple of 4) but the HEIGHT was being snapped: 44*1.5 = 66, CellUnit(44)
    // = 4, 66 % 4 = 2, tie -> UP -> 68. So a 68px-tall sheet was drawn into a
    // 66px window and the picture sat low with a light band above it.
    // Snapping that height satisfies a divide the engine never performs.
    //
    // THIS IS NOT A JUDGEMENT CALL - THE PROJECT'S OWN GATE ALREADY SPECIFIES
    // IT. tools\uimap\emu\gate_namicons.py:131 asserts
    //     (w, h) == (4 * round(w0 * f / 4), lround(h0 * f))
    // i.e. snap the WIDTH to the 4-state cell, take the HEIGHT exactly. For
    // 176x44 at 1.5 that is 264x66. The gate has been RED on the 15x row since
    // 15:04 today, green on 2x and 3x throughout - a built-in positive control.
    //
    // ⚠ DO NOT MAKE THIS THE GLOBAL DEFAULT. Measured across the 2280 pristine
    // PNGs, dropping the height snap everywhere moves 791 sheets (176x44 x326,
    // 87x93 x120, 129x129 x24, 160x36 x23) and puts #143's white-seam fix back
    // in play across the whole game. It is scoped to the strip families on
    // purpose.
    //
    // No-op at an integer factor: ScaleDim returns before CellUnit is consulted.
    private static bool sNoHeightSnap = false;          // set PER FILE, below
    private static readonly HashSet<uint> sHeightExactGroups = new HashSet<uint>();
    // #162: derived state strips whose HEIGHT must be exact (--height-exact-strips).
    private static readonly HashSet<ulong> sHeightExactStrips = new HashSet<ulong>();

    // #175: --smooth-unkeyed. See UpscaleSmoothUnkeyed for the full rationale.
    private static bool sSmoothUnkeyed = false;
    private static int sSmoothed = 0;        // counters for the run summary
    private static int sSmoothSkippedKeyed = 0;
    private static int sSmoothSkippedInteger = 0;
    // #171/#165: how many sheet widths took the cell-first rule, and how many
    // were a no-snap/cell-strip CONTRADICTION left on the no-snap rule. Both are
    // printed in the run summary - a silent 0 here at a fractional factor means
    // cell-strips.txt never reached the tool (law 54: no log line = did not run).
    private static int sCellFirst = 0;
    private static int sCellFirstConflict = 0;
    // #175 second half: --smooth-keyed. Smooth sheets that CONTAIN the FF00FF
    // colour key, by excluding the key from every average and re-applying it by
    // coverage. Off unless asked for; the unkeyed path is unchanged.
    private static bool sSmoothKeyed = false;
    private static int sSmoothedKeyed = 0;
    private static int sSmoothSkippedFineKey = 0;

    // ⛔ CELL-FIRST STRIP SIZING (#171 / #165, 2026-08-16). SCALE THE UNIT AND
    // MULTIPLY - NEVER SCALE THE TOTAL. This is the #170 leaf rule transposed
    // from windows to art, and it is the cure the comment above kCellCounts
    // already named ("states * ScaleRound(w,f)") and then rejected:
    //
    //     "which this tool cannot know - it runs over a directory and never
    //      sees a .UI"
    //
    // THAT OBJECTION PREDATES --cell-strips AND IS NO LONGER TRUE. It assumed
    // the sheet had to be sized from its CONSUMER'S WINDOW, which this tool
    // genuinely cannot see. It does not. It needs the CELL, and the cell is
    // v / states, where states already arrives per-file as sStripStates from
    // find_cell_strips.py. No window is ever consulted.
    //
    // ⚠ THIS IS NOT THE REVERTED fit_state_strips_to_windows (#148). That one
    // sized strips from their CONSUMER'S WINDOW and died because runtime-created
    // consumers appear in NO .UI, so its conflict check reported 0 falsely and it
    // broke the disaster flyout thumbnails on hover. This rule never looks at a
    // window, so that failure mode cannot occur here.
    //
    // WORKED EXAMPLES, both measured:
    //   #171 Zoom Out   84 wide, 4 states, cell 21
    //                   old: R(84*1.5)=126 -> snap LCM{3,4}=12 -> 132, cell 33,
    //                        but the window is R(21*1.5) = 32.  MISMATCH.
    //                   new: 4 * R(21*1.5) = 4 * 32 = 128, cell 32.  EXACT.
    //   #165 radiocheck 136 wide, 8 states, cell 17
    //                   old: R(136*1.5)=204, 204/8 = 25.5 - every state miscuts,
    //                        and BuildSampleMap DECLINED SILENTLY (outLen%k!=0).
    //                   new: 8 * R(17*1.5) = 8 * 26 = 208, cell 26.  EXACT.
    //
    // ⚠ PROVABLE NO-OP AT AN INTEGER FACTOR, and the early return below is the
    // proof rather than a claim: for integer k, R(c*k)*n == c*k*n == R(c*n*k),
    // so cell-first and total-first agree exactly and this branch is never even
    // reached. 2x and 3x must come back with ZERO differing entry payloads.
    //
    // ⚠ THE SNAP IS SKIPPED, NOT APPLIED AFTERWARDS. CellUnit exists to protect
    // a cell divide; here the divide is exact BY CONSTRUCTION, so snapping could
    // only move the sheet back off the cell it just landed on.
    private static int ScaleDim(int v, double factor, bool stripAxis = false)
    {
        int s = (int)Math.Floor(v * factor + 0.5);   // round-half-up, as before
        if (factor == Math.Floor(factor)) return s;  // integer: already exact

        if (stripAxis && sStripStates > 1 && v % sStripStates == 0)
        {
            // A no-snap sheet's contract is "equal your window exactly", which is
            // a DIFFERENT rule from "divide into N equal cells". A sheet in both
            // lists is a contradiction we must SEE rather than silently resolve,
            // so it is counted and left on the no-snap rule (#160).
            if (sNoSnapThis) { sCellFirstConflict++; }
            else
            {
                sCellFirst++;
                int cell = (int)Math.Floor((double)v / sStripStates * factor + 0.5);
                return sStripStates * cell;
            }
        }

        int k = CellUnit(v);
        if (k <= 1 || s % k == 0) return s;
        int down = s - (s % k);
        int up = down + k;
        // Ties go UP: art that is a shade too big can never under-cover its
        // destination, and under-coverage is the gap that shows as a seam.
        int snapped = (s - down < up - s) ? down : up;
        if (snapped < k) { snapped = k; }
        // ⚠ PROPORTIONALITY GUARD. A 16px icon is divisible by 16, but it is an
        // ICON, not a 16-cell strip; snapping it to the nearest multiple of 16
        // would move it by 8px - a 33% distortion - to satisfy a cut that sheet
        // does not have. If the correction exceeds 12.5% of the dimension the
        // divisor is almost certainly a coincidence of the number rather than a
        // real cell count, so leave the dimension alone. Every genuine cell
        // sheet measured here is far larger than its cell count, so the real
        // cases are corrections of 2-6px on 100-5000px sheets and pass easily.
        if (Math.Abs(snapped - s) * 8 > s) { return s; }
        return snapped;
    }

    // Nearest-neighbor upscale by an arbitrary factor. Every output pixel is an
    // EXACT copy of the source pixel at floor(o/factor) (clamped) - no Graphics,
    // no resampling, no premultiplication: alpha and any colorkey are preserved
    // byte-for-byte. For integer factors this is exact NxN block replication
    // (2x output is byte-identical to the original tool). For 1.5 it produces a
    // crisp 2:1 pixel-doubling pattern (the least-soft option; zero bleed).
    private static Bitmap UpscaleNearest(Bitmap src, double factor)
    {
        int w = src.Width, h = src.Height;
        // stripAxis: true on WIDTH only. A horizontal strip has no vertical
        // divide, so a height that happens to divide by the state count is an
        // arithmetic coincidence, not a cell cut (same reasoning as mapX below).
        int ow = ScaleDim(w, factor, true);
        int oh = sNoHeightSnap ? (int)Math.Floor(h * factor + 0.5) : ScaleDim(h, factor);
        var dst = new Bitmap(ow, oh, PixelFormat.Format32bppArgb);
        BitmapData sd = src.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        BitmapData dd = dst.LockBits(new Rectangle(0, 0, ow, oh), ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
        try
        {
            // read entire source
            var s = new int[h][];
            for (int y = 0; y < h; y++)
            {
                s[y] = new int[w];
                Marshal.Copy(Ofs(sd.Scan0, (long)y * sd.Stride), s[y], 0, w);
            }
            // ⛔ MAP BY THE FACTOR, NOT BY THE SIZE RATIO. (#151, 2026-08-09.)
            //
            // This used to be `sx = ox * w / ow` unconditionally - the ACTUAL
            // SIZE RATIO - on the reasoning that when ScaleDim snaps the output
            // to keep a cell divide exact, ow is no longer w*factor, so
            // ox/factor would stop short of the source instead of resampling
            // all of it.
            //
            // THE REASONING WAS SOUND AND THE PREMISE WAS FALSE. Measured over
            // the 284 distinct dimension values in the whole pristine 1x corpus
            // (2280 PNGs): ScaleDim snaps DOWN in ZERO cases, and produces an
            // output below v*factor in ZERO cases (126 exactly equal, 158
            // above). Ties go UP at :496. So the factor map can only ever
            // duplicate a trailing edge pixel - it can NEVER crop - and the
            // hazard this branch was written for does not exist here.
            //
            // WHAT IT COST: the ratio map RE-TIMES every feature inside the
            // sheet. Same dimensions, different pixels. The advisor briefing
            // sheet {46A006B0,1401557C} is 528x143 in BOTH the 2026-08-03 build
            // and the broken one, but its viewport aperture moved from (3,3) to
            // (3,4); the My Sim portrait frame {46A006B0,13F1525E} moved its
            // opaque bbox from x[3..60) to x[4..61). Simulating both maps
            // reproduces exactly those two results, which is what proves the
            // sampler and not the dimensions. On screen: portraits and advisor
            // faces sitting high and left inside frames that are themselves the
            // right size. USER-CONFIRMED, and user-confirmed cured by this.
            //
            // ⚠ ZERO DIMENSIONS CHANGE HERE. Every consumer's cut arithmetic
            // (width/4, width/3, width/12) sees exactly the numbers it saw
            // before. This changes only WHICH SOURCE PIXEL each output pixel
            // copies - which is why it is safe where an art-DIMENSION change is
            // not (see REGRESSION.md #148: art binds by TGI and some consumers
            // are created at runtime and appear in no .UI).
            //
            // The ratio map is KEPT as a guarded fallback for the case its
            // author had in mind. It is never taken in this corpus; if a future
            // sheet ever does snap down, it resamples the whole image rather
            // than cropping it.
            //
            // INTEGER FACTORS ARE BYTE-IDENTICAL EITHER WAY: ow == w*factor
            // exactly, so ox*w/ow == floor(ox/factor) and the guard is always
            // true. Proven per build by an entry-level hash diff, not asserted.
            // WIDTH only. A horizontal strip has no vertical divide, so the
            // height keeps the map it has always had (--height-exact-group
            // exists for the same reason).
            var mapX = BuildSampleMap(w, ow, factor, sStripStates);
            bool factorMapY = oh >= (long)Math.Floor(h * factor);
            var drow = new int[ow];
            for (int oy = 0; oy < oh; oy++)
            {
                int sy = factorMapY ? (int)(oy / factor) : (int)((long)oy * h / oh);
                if (sy >= h) sy = h - 1;
                int[] srow = s[sy];
                for (int ox = 0; ox < ow; ox++) drow[ox] = srow[mapX[ox]];
                Marshal.Copy(drow, 0, Ofs(dd.Scan0, (long)oy * dd.Stride), ow);
            }
        }
        finally
        {
            src.UnlockBits(sd);
            dst.UnlockBits(dd);
        }
        return dst;
    }

    // High-quality factor upscale: HighQualityBicubic with the alpha-safe recipe:
    //  - CompositingMode.SourceCopy  : output = resampled source, never blended
    //                                  over the (transparent black) destination
    //  - PixelOffsetMode.Half        : sample grid aligned to pixel centers, no
    //                                  half-pixel shift / edge crop
    //  - ImageAttributes TileFlipXY  : edge texels are mirrored instead of
    //                                  sampling transparent black outside the
    //                                  image, so borders don't get dark fringes
    // ⛔ #175 - SMOOTH RESAMPLE, BUT ONLY WHERE IT PROVABLY CANNOT FRINGE.
    //
    // WHY THIS IS NOT --hq COMING BACK. The ⛔ block at the top of Main rejects
    // --hq twice, and it is right about what it measured: Graphics.DrawImage
    // over the RAW keyed bitmap lets magenta 0xFF00FF - this game's
    // TRANSPARENCY KEY, not a colour - take part in a colour average, so an
    // exact key pixel becomes 0xFE01FE, the key test misses it, and the key
    // DRAWS. That is what turned the Mayor Rating bar pink (#143).
    //
    // That is a fact about letting the key into the arithmetic. It is NOT a
    // fact about smoothing. This path sidesteps it by the only honest route:
    // IT REFUSES TO TOUCH ANY SHEET THAT CONTAINS THE KEY AT ALL. Measured over
    // a 392-sheet sample of the 2280-sheet corpus: 21% contain an exact FF00FF
    // and 79% contain none whatsoever. This handles the 79% and leaves the
    // keyed remainder on nearest-neighbour, byte-for-byte as today.
    //
    // WHAT IT FIXES. At f=1.5 nearest-neighbour gives a RAGGED pixel grid:
    // measured on advisor sheet 14015571, column runs are 1px x106 and 2px x110,
    // where 2x is 2px x216 and 3x is 3px x216, both perfectly uniform. Half the
    // strokes come out one pixel wide and half two, so every curve and bevel has
    // inconsistent thickness. Nothing is blended, yet it reads as blur. That is
    // the "softness at 1.5x" the user reported, and it is inherent to 3/2.
    //
    // ⚠ THE OUTPUT DIMENSIONS DO NOT CHANGE. ScaleDim still decides them,
    // exactly as for the nearest path. Changing art dimensions has the scope of
    // the WHOLE GAME (law 66) and is what #143 and the #156 backout were; this
    // changes pixel CONTENT only, at identical sizes and identical cell
    // boundaries.
    //
    // ⚠ FRACTIONAL FACTORS ONLY. At an integer factor nearest-neighbour is
    // already an exact NxN block replicate - there is nothing to improve and
    // everything to lose, because 2x and 3x are user-confirmed. Refusing here
    // is what keeps their entry payloads identical.
    //
    // ⚠ PER-CELL, ALWAYS. A state strip's cells are independent images that
    // happen to share a PNG. Filtering across a cell boundary would blend state
    // N+1 into state N - which is exactly the defect #169 removed. Each block is
    // resampled from its own source block only, so a cell can never see its
    // neighbour.
    //
    // Kernel is Catmull-Rom (separable, 4-tap, interpolating). Alpha is
    // resampled premultiplied so a transparent texel cannot drag colour toward
    // black at an edge.
    private static bool HasExactColorKey(Bitmap src)
    {
        int w = src.Width, h = src.Height;
        BitmapData sd = src.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        try
        {
            var row = new int[w];
            for (int y = 0; y < h; y++)
            {
                Marshal.Copy(Ofs(sd.Scan0, (long)y * sd.Stride), row, 0, w);
                for (int x = 0; x < w; x++)
                {
                    // opaque, exactly FF00FF
                    if ((row[x] & 0x00FFFFFF) == 0x00FF00FF) { return true; }
                }
            }
        }
        finally { src.UnlockBits(sd); }
        return false;
    }

    // ⛔ FINE-KEY GUARD (#175, 2026-08-16). MEASURED, and it reversed a decision.
    //
    // Key-aware smoothing is right for a sheet whose key is a large REGION - an
    // icon on a transparent field, a silhouette. It is WRONG for a sheet whose
    // key is 1px STRUCTURE, and the HUD Mayor Rating ladder proved it:
    //
    //   1x design      ink widths {3,4}   key gaps {1,2}
    //   2x NN (good)   ink {6,8}          gaps {2,4}      <- both distinctions kept
    //   1.5x NN        ink {4,5,6}        gaps {1,2,3}    <- ragged but STRUCTURED
    //   1.5x smoothed  ink {4,5,7}        gaps {2}        <- gaps COLLAPSED to one
    //
    // Re-keying at half coverage homogenised a 1px gap and a 2px gap into the
    // same 2px gap, destroying a distinction the artist drew and that 2x keeps.
    // A 1px feature at f=1.5 is below what ANY resampler can carry; nearest
    // neighbour is genuinely the better answer there, ragged or not.
    //
    // So: refuse the keyed path when the sheet's SMALLEST key run is 1-2px. This
    // is measured per sheet, never a hand-list. Sheets whose key is a broad
    // region are unaffected and still get smoothed.
    private static int MinKeyRun(Bitmap src)
    {
        int w = src.Width, h = src.Height, min = int.MaxValue;
        BitmapData sd = src.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        try
        {
            var row = new int[w];
            for (int y = 0; y < h; y++)
            {
                Marshal.Copy(Ofs(sd.Scan0, (long)y * sd.Stride), row, 0, w);
                int run = 0;
                for (int x = 0; x < w; x++)
                {
                    bool k = (row[x] & 0x00FFFFFF) == 0x00FF00FF;
                    if (k) { run++; }
                    else if (run > 0) { if (run < min) { min = run; } run = 0; }
                }
                if (run > 0 && run < min) { min = run; }
            }
        }
        finally { src.UnlockBits(sd); }
        return (min == int.MaxValue) ? 0 : min;
    }

    private static double CatRom(double t)
    {
        double a = Math.Abs(t);
        if (a <= 1.0) { return 1.5 * a * a * a - 2.5 * a * a + 1.0; }
        if (a <= 2.0) { return -0.5 * a * a * a + 2.5 * a * a - 4.0 * a + 2.0; }
        return 0.0;
    }

    // ⛔ KEY-AWARE MODE (#175 second half, 2026-08-16). `keyed == true` lets this
    // run on a sheet that CONTAINS the FF00FF colour key, which the unkeyed path
    // refuses outright.
    //
    // WHY THE BLANKET REFUSAL WAS TOO WIDE. The --hq ban is real and it is about
    // ONE THING: letting the key into the arithmetic. Graphics.DrawImage averages
    // an exact FF00FF with its neighbours, the result is 0xFE01FE, the key test
    // misses it, and the key DRAWS. That is what turned the Mayor Rating bar pink
    // (#143). But that is a fact about ADMITTING THE KEY TO THE AVERAGE, not
    // about smoothing, and 465 sheets were being refused for it.
    //
    // WHAT THIS DOES INSTEAD. The key is treated as ABSENCE, exactly as the
    // engine treats it - never as a colour:
    //   * every key pixel gets weight ZERO and contributes NOTHING to any sum;
    //   * each output pixel divides by the COVERAGE actually accumulated, so a
    //     pixel near a key boundary is the average of the real pixels only;
    //   * an output pixel whose coverage falls below half is re-keyed to an
    //     EXACT FF00FF, so the transparent region stays exactly transparent and
    //     its outline stays crisp instead of dissolving into a halo.
    // The key colour therefore never appears in a sum, and no intermediate value
    // can drift onto or off the key by accident.
    //
    // ⚠ STILL DO NOT PREMULTIPLY - see the block below. That lesson is
    // independent of this one and cost its own build.
    //
    // ⚠ INTEGER FACTORS ARE UNAFFECTED: the caller refuses smoothing outright at
    // an integer factor (nearest is already an exact NxN replicate), so this
    // cannot move 2x or 3x by a single byte.
    private static Bitmap UpscaleSmoothUnkeyed(Bitmap src, double factor, bool keyed = false)
    {
        int w = src.Width, h = src.Height;
        // stripAxis: true on WIDTH only. A horizontal strip has no vertical
        // divide, so a height that happens to divide by the state count is an
        // arithmetic coincidence, not a cell cut (same reasoning as mapX below).
        int ow = ScaleDim(w, factor, true);
        int oh = sNoHeightSnap ? (int)Math.Floor(h * factor + 0.5) : ScaleDim(h, factor);

        // Cell blocks: only if the derived state count divides BOTH sides, the
        // same guard BuildSampleMap uses. Otherwise one block = the whole image.
        int k = sStripStates;
        int nb = (k > 1 && w % k == 0 && ow % k == 0) ? k : 1;
        int sbw = w / nb, obw = ow / nb;

        var srcPx = new int[h][];
        var dst = new Bitmap(ow, oh, PixelFormat.Format32bppArgb);
        BitmapData sd = src.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        try
        {
            for (int y = 0; y < h; y++)
            {
                srcPx[y] = new int[w];
                Marshal.Copy(Ofs(sd.Scan0, (long)y * sd.Stride), srcPx[y], 0, w);
            }
        }
        finally { src.UnlockBits(sd); }

        // ⛔ DO NOT PREMULTIPLY. THIS COST A BUILD - 2026-08-16.
        //
        // The first version of this function premultiplied RGB by alpha, which
        // is the textbook right answer for an ALPHA-composited image. SC4 is
        // not one. Its transparency is the COLOUR KEY; the alpha channel in
        // these PNGs is frequently 0 over pixels whose RGB still carries the
        // real picture. Premultiplying zeroed that RGB and un-premultiplying
        // could not recover it, so the advisor card came out SOLID BLACK and
        // high-contrast edges grew coloured speckles.
        //
        // Nearest-neighbour - the reference behaviour we are matching - copies
        // all four channels independently and never mixes alpha into colour.
        // Do exactly that, just with a wider kernel. Colour-keyed sheets are
        // already refused upstream, so there is no key to protect here either.
        var pa = new double[h, w]; var pr = new double[h, w];
        var pg = new double[h, w]; var pb = new double[h, w];
        // pk = COVERAGE mask: 1.0 for a real pixel, 0.0 for a key pixel. In
        // unkeyed mode every pixel is real, so the maths below reduces EXACTLY to
        // the previous behaviour (every coverage sum becomes wsum and cancels).
        var pk = new double[h, w];
        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                int p = srcPx[y][x];
                bool isKey = keyed && (p & 0x00FFFFFF) == 0x00FF00FF;
                pk[y, x] = isKey ? 0.0 : 1.0;
                pa[y, x] = (p >> 24) & 0xFF;
                pr[y, x] = (p >> 16) & 0xFF;
                pg[y, x] = (p >> 8) & 0xFF;
                pb[y, x] = p & 0xFF;
            }
        }

        // horizontal pass, per block; then vertical over the whole image
        var ha = new double[h, ow]; var hr = new double[h, ow];
        var hg = new double[h, ow]; var hb = new double[h, ow];
        var hk = new double[h, ow];   // coverage carried through the H pass
        for (int b = 0; b < nb; b++)
        {
            int sx0 = b * sbw, ox0 = b * obw;
            for (int o = 0; o < obw; o++)
            {
                double c = (o + 0.5) * sbw / obw - 0.5;
                int i0 = (int)Math.Floor(c) - 1;
                double wsum = 0.0, aa = 0, rr = 0, gg = 0, bb = 0;
                var wts = new double[4]; var idx = new int[4];
                for (int t = 0; t < 4; t++)
                {
                    int si = i0 + t;
                    double wt = CatRom(c - si);
                    if (si < 0) { si = 0; } else if (si >= sbw) { si = sbw - 1; }
                    idx[t] = sx0 + si; wts[t] = wt; wsum += wt;
                }
                if (wsum == 0.0) { wsum = 1.0; }
                for (int y = 0; y < h; y++)
                {
                    aa = rr = gg = bb = 0;
                    double kk = 0;
                    for (int t = 0; t < 4; t++)
                    {
                        double wt = wts[t]; int si = idx[t];
                        // A key pixel contributes NOTHING: its weight is scaled by
                        // a coverage of 0, so the key colour never enters a sum.
                        double cw = wt * pk[y, si];
                        aa += cw * pa[y, si]; rr += cw * pr[y, si];
                        gg += cw * pg[y, si]; bb += cw * pb[y, si];
                        kk += cw;
                    }
                    // Divide by the coverage actually accumulated, not by wsum -
                    // otherwise a pixel beside the key would be darkened toward
                    // black in proportion to how much key it touched.
                    double den = (kk != 0.0) ? kk : 1.0;
                    ha[y, ox0 + o] = aa / den; hr[y, ox0 + o] = rr / den;
                    hg[y, ox0 + o] = gg / den; hb[y, ox0 + o] = bb / den;
                    hk[y, ox0 + o] = kk / wsum;   // normalised 0..1 coverage
                }
            }
        }

        BitmapData dd = dst.LockBits(new Rectangle(0, 0, ow, oh), ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
        try
        {
            var orow = new int[ow];
            for (int oy = 0; oy < oh; oy++)
            {
                double c = (oy + 0.5) * h / oh - 0.5;
                int j0 = (int)Math.Floor(c) - 1;
                var wts = new double[4]; var idx = new int[4]; double wsum = 0.0;
                for (int t = 0; t < 4; t++)
                {
                    int sj = j0 + t;
                    double wt = CatRom(c - sj);
                    if (sj < 0) { sj = 0; } else if (sj >= h) { sj = h - 1; }
                    idx[t] = sj; wts[t] = wt; wsum += wt;
                }
                if (wsum == 0.0) { wsum = 1.0; }
                for (int ox = 0; ox < ow; ox++)
                {
                    double aa = 0, rr = 0, gg = 0, bb = 0, kk = 0, kw = 0;
                    for (int t = 0; t < 4; t++)
                    {
                        double wt = wts[t]; int sj = idx[t];
                        double cw = wt * hk[sj, ox];
                        aa += cw * ha[sj, ox]; rr += cw * hr[sj, ox];
                        gg += cw * hg[sj, ox]; bb += cw * hb[sj, ox];
                        kw += cw; kk += wt * hk[sj, ox];
                    }
                    double vden = (kw != 0.0) ? kw : 1.0;
                    aa /= vden; rr /= vden; gg /= vden; bb /= vden;
                    // ⭐ RE-KEY BY COVERAGE. Below half coverage the destination
                    // pixel is more absence than picture, so it becomes an EXACT
                    // FF00FF again. This is what keeps a transparent region
                    // exactly transparent and its outline crisp - without it a
                    // smoothed keyed sheet grows a translucent halo where the
                    // engine expects a hard edge.
                    if (keyed && (kk / wsum) < 0.5)
                    {
                        orow[ox] = unchecked((int)0xFFFF00FF);
                        continue;
                    }
                    // Straight channels, each clamped to [0,255]. Catmull-Rom
                    // overshoots slightly at a hard edge; clamping is what keeps
                    // that from wrapping into a bright speckle.
                    int A = (int)Math.Round(aa);
                    int R = (int)Math.Round(rr), G = (int)Math.Round(gg), B = (int)Math.Round(bb);
                    if (R < 0) R = 0; else if (R > 255) R = 255;
                    if (G < 0) G = 0; else if (G > 255) G = 255;
                    if (B < 0) B = 0; else if (B > 255) B = 255;
                    if (A < 0) A = 0; else if (A > 255) A = 255;
                    // ⛔ BELT AND BRACES. This path never runs on a sheet that
                    // contains the key, so it cannot BLEED one - but Catmull-Rom
                    // overshoot could in principle MANUFACTURE an exact FF00FF
                    // out of neighbouring reds and blues. If that ever happens
                    // the pixel would silently turn transparent in game. Nudge
                    // it off the key by one level; visually identical, and it
                    // makes "no new key pixels" true by construction.
                    if (R == 0xFF && G == 0x00 && B == 0xFF) { G = 1; }
                    orow[ox] = (A << 24) | (R << 16) | (G << 8) | B;
                }
                Marshal.Copy(orow, 0, Ofs(dd.Scan0, (long)oy * dd.Stride), ow);
            }
        }
        finally { dst.UnlockBits(dd); }
        return dst;
    }

    private static Bitmap UpscaleHq(Bitmap src, double factor)
    {
        int w = src.Width, h = src.Height;
        // stripAxis: true on WIDTH only. A horizontal strip has no vertical
        // divide, so a height that happens to divide by the state count is an
        // arithmetic coincidence, not a cell cut (same reasoning as mapX below).
        int ow = ScaleDim(w, factor, true);
        int oh = sNoHeightSnap ? (int)Math.Floor(h * factor + 0.5) : ScaleDim(h, factor);
        var dst = new Bitmap(ow, oh, PixelFormat.Format32bppArgb);
        using (var g = Graphics.FromImage(dst))
        using (var ia = new ImageAttributes())
        {
            ia.SetWrapMode(WrapMode.TileFlipXY);
            g.CompositingMode = CompositingMode.SourceCopy;
            g.CompositingQuality = CompositingQuality.HighQuality;
            g.InterpolationMode = InterpolationMode.HighQualityBicubic;
            g.PixelOffsetMode = PixelOffsetMode.Half;
            g.SmoothingMode = SmoothingMode.None;
            g.DrawImage(src, new Rectangle(0, 0, ow, oh), 0, 0, w, h, GraphicsUnit.Pixel, ia);
        }
        return dst;
    }

    private static IntPtr Ofs(IntPtr basePtr, long offset)
    {
        return new IntPtr(basePtr.ToInt64() + offset);
    }
}
