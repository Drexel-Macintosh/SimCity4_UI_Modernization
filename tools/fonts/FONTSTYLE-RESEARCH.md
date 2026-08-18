# SimCity 4 FontStyle.ini — Research Notes (2026-07-21)

Goal: double all UI font sizes to match the runtime layer that already doubles every UI window.
Target: SimCity 4 Deluxe 1.1.641 (Steam), install `C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\`.

> ## ✅ ADDENDUM 2026-07-29 — THE "FONT SIZE DOESN'T WORK FOR NEWS"
> ## LIMITATION IS SOLVED (and it was never a FontStyle problem)
>
> Both community precedents below, and the "Gotchas" list, record that news
> text ignores font-size changes. **Cause found:** news/story/tutorial/popup/
> Credits text is not drawn from a FontStyle style at all — it goes through the
> game's own **HTML renderer**, whose `SIZE=1..7` indexes resolve via two
> point-size tables in `.rdata` (`0xACD4A0` fonts, `0xAB4AD0` headings). No
> FontStyle edit — loose file or DBPF — can reach them, which is exactly why
> the DAT-based mods hit this wall.
>
> **Fixed in SC4UIScale v2.19.0** by scaling those two tables at `PostAppInit`
> (`CodePatches::ApplyHtmlSizeScale`, verify-before-write). Each rich window
> COPIES the tables at creation, so one patch reaches every instance.
>
> **Coupled consequence for THIS file:** the advisor/message popup builders
> derive an HTML size index from a *style's* size (`idx = (4*size+8)/18`), so
> the popup GUIDs are retargeted at two **stock-size clone styles**,
> `MessageHeaderHtml` (0x5c4b0914) and `MessageBodyHtml` (0x5c4b0915), which
> every FontStyle tier file now carries. **Those two must stay at STOCK sizes
> at every tier** — doubling them compounds against the scaled tables and the
> popups render ~4x. Full detail + trap signatures: `_tests\REGRESSION.md`
> ("NEWS BOX + NEWS TEXT = THE HTML ENGINE").

## TL;DR

- The install ships **no** `FontStyle.ini` anywhere (confirmed: recursive scan of the whole install tree, including root and `Apps\`). All font styles live in a "Font Table" INI **inside `SimCity_1.dat`** (TGI `0x00000000, 0x4A87BFE8, 0x2A87BFFC`).
- The 1.1.641 exe **does** contain a loose-file override path. Confirmed by disassembling `Apps\SimCity 4.exe`: at startup the font system probes
  1. `<GetPluginDirectory()>\FontStyle.ini` → **`<install>\Plugins\FontStyle.ini`**
  2. `<GetDataDirectory(0)>\FontStyle.ini` → **`<install>\FontStyle.ini`** (install root)
  3. fallback: extracts the DBPF Font Table (TGI above) to a temp file and parses that.
- **Recommended placement: install root** — `C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\FontStyle.ini`. (A copy in `Plugins\` would take priority over root; avoid having both.)
- `FontStyle.candidate.ini` (this folder) = the exact default table with all **88** style sizes doubled, nothing else changed. `FontStyle.default.ini` = the pristine extracted default, for diffing and per-style reverts.

## Where the game looks (binary evidence, 1.1.641)

Disassembly of `Apps\SimCity 4.exe` (the patched Steam 1.1.641 binary actually on disk), font-init function at VA `0x44db60`–`0x44e2ab`:

- `0x44dc8d`: virtual call `cISC4App` vtable **+0xDC** = `GetPluginDirectory(cIGZString&)` (1 arg), then appends the literal `"FontStyle.ini"` (string at VA `0xA86DC8`, xrefs `0x44dc9d`, `0x44dcd6`).
- `0x44dcb0`: helper `0x919e96` = file-exists check (`GetFileAttributesA`-style, `cmp eax, -1`).
- If missing → `0x44dcc6`: virtual call vtable **+0xD4** = `GetDataDirectory(cIGZString&, int32 index)` (2 args, `index=0` pushed) + `"FontStyle.ini"`, exists-check again.
- If still missing → `0x44dd2e`–`0x44dd41`: builds resource key `{type 0x00000000, group 0x4A87BFE8, instance 0x2A87BFFC}` and materializes the DBPF INI to a temp file.
- Whichever file won is parsed: section `[Font Aliases]` first (`0x44dd7e`), then `[Font Styles]` (`0x44de22`). Section-name strings sit in `.rdata` directly beside `FontStyle.ini`.

Vtable identification: method order from the community GZCOM header `cISC4App.h` (nsgomez/gzcom-dll); `+0xD4` = method #51 `GetDataDirectory(out, index)` (only 2-arg method in that region — matches the call), `+0xDC` = #53 `GetPluginDirectory(out)` (1 arg — matches).

Directory resolution: `Apps\SimCity 4.ini` (next to the exe) defines
```
[Directories]
Data=..\
PlugIn=..\Plugins\
```
so Data dir = install root and Plugin dir = `<install>\Plugins\`, both relative to the exe's folder (`Apps\`). Note `GetPluginDirectory` is the *game-folder* Plugins, not `Documents\SimCity 4\Plugins` (that is `GetUserPluginDirectory`, not probed here).

Consequences:
- The loose file **wins over** the DBPF copy and over any plugin .dat that overrides the TGI (the loose-file check happens before the resource-manager fallback).
- It is a **whole-file replacement, not a merge** — ship every style, not just the changed ones. (Styles are looked up by GUID; a missing style would fall back to `Default`/fail depending on call site. Don't find out — include all.)

## File format

Authoritative spec: Maxis' own comment header inside the file (preserved verbatim at the top of `FontStyle.default.ini`), matching the SC4D Encyclopaedia "Font Table" article.

Sections, in the order the game parses them:
- `[Font Styles]` — one line per style:
  `<style name> = "<face[, fallback face...]>", "<size>", "<param|param|...>", <GUID>`
  - **style name**: identifier used in UI scripts; **GUID**: the hex id the engine binds UI elements to. **Never change names or GUIDs.**
  - **size**: quoted integer, game points (Maxis note: ≈ Photoshop points at 74.72 px/inch). No documented upper bound; defaults range 10–32; renderer is Font Fusion (since the 7/21/2003 patch era — this comment is in the shipped file, so 1.1.641 is the Font Fusion engine).
  - **params** (from the in-file spec): `Bold`, `Italic`, `Underline`, `Strikethrough`, `Shadow`, `XScale=0.1..10.0`, `YScale=0.1..10.0`, `XAdvanceScale=0.1..10.0`, `AA=None|BG|Color`, `Color=r,g,b`, `BGColor=r,g,b`, `Gamma=0.0..10.0`, `Sharpness=float`, `CharSpacing=-10..+10` (px), `LineSpacing=-10..+10` (px). Params are case-insensitive in practice (defaults use `bold|aa=bg`; Maxis' own header uses mixed case) and even truncated tokens appear (`under` in `BdgtLedgerLineLiteUnder`).
- `[Font Aliases]` — `Alias name = Actual name` (default: `Arta Medium TT = Arta`).
- `[Directories]` — `Fonts=Fonts\`; per Maxis' comment it "only applies to applications that use this file but don't know where to find the font files"; keep verbatim anyway.
- Comments: `;` lines. The shipped file even opens with a stray backtick line, so the parser is lenient — still, keep the candidate byte-conservative. File is plain ASCII, CRLF.

Default faces: `Arta` (body/italic) and `StocletITC TT` (headers/bold) — both embedded/installed by the game; `Arial MT, Arial` for dev styles; `SimDingbat` for symbols. The exe carries CJK fallbacks (`MHei GB`, `HG-Gothic`, `Hy Round Gothic`, `MHei B5`, files in `<install>\Fonts\*.mxf`) for localized SKUs — not touched by this work.

## Does it work on 1.1.641, and gotchas

- The probe code is **in the 1.1.641 Steam exe on disk** — this is direct evidence, stronger than any forum post. What is *not* yet proven is the end-to-end visual result; nobody in the community appears to have published a loose-FontStyle.ini mod (they edited the DAT instead, see below).
- Gotchas:
  - Whole-file replacement (see above) — all 88 styles + aliases must be present.
  - Probed once at startup (font-system init) — edits require a game restart.
  - `Plugins\FontStyle.ini` silently shadows the root copy.
  - Keep GUIDs, names, faces, params identical; change sizes only (that is exactly what the candidate does).
  - Community DAT-based precedent reports the **news ticker/news text ignores size changes** and **large numbers overflow fixed layouts** — expect the same here.

## Community precedents

- **"Increase font size"** (Simtropolis STEX file 30826): a plugin .dat with an edited Font Table (made with iLive Reader), recommended for 1920x1080. Author-reported limitations: *"font size does not work for news"*, and big numbers don't fit their boxes. Proves sizes can be raised well above stock and the game keeps running. (Page is behind Simtropolis' bot checkpoint; details taken from search-result snippets of the file description.)
- **"Font Size Adjustment"** thread (Simtropolis topic 760505): same situation (checkpoint); search snippets confirm the ilive_reader/.dat route as the known method.
- SC4D forum "Modding SimCity 4 Fonts" (topic 13344): unanswered 2011 request — no info.
- No published attempt at a *loose* FontStyle.ini override was found; the DAT route was the community's path. The loose route is cleaner for us: no DBPF tooling, trivially reversible, and it outranks plugin DATs.

## Can sizes be scaled arbitrarily (x2)?

Yes — size is a free integer field per style; the candidate doubles 10–32 pt defaults to 20–64 pt. Alternative/extra knobs if plain size x2 misbehaves for a style: `XScale`/`YScale` (0.1–10.0) scale glyphs without changing the layout engine's nominal size, and `XAdvanceScale` adjusts spacing — useful for targeted fixes. Expected side effects:
- Text overflow in elements whose boxes are *not* doubled by the runtime layer; with the window-doubling layer active the boxes should match again.
- Styles that likely draw **outside** the doubled UI windows — review on first test and revert individually if oversized: `Signpost`, `Label` (in-world sign/label billboards), `SnapshotTaker` (snapshot stamp), `LoadScreenTitle`/`LoadScreenGoofyMessage` (load screen).
- `LineSpacing`/`CharSpacing` pixel tweaks (1–4 px in defaults) were deliberately **not** doubled — they're clamped to ±10 and visually minor; doubling them is a follow-up option if line stacking looks tight.
- Glyph texture cache pressure grows ~4x per style in use; sizes ≤64 pt are modest, no crash expected.

## Candidate file basis (provenance chain)

1. `SimCity_1.dat` → DBPF index entry TGI `0x00000000, 0x4A87BFE8, 0x2A87BFFC` (the only Font Table in all 10 .dat files of the install — EP1.dat does not override it) → QFS-decompressed to 22,396 bytes → saved verbatim as `FontStyle.default.ini`.
2. `FontStyle.candidate.ini` = same bytes + 5-line comment header, with exactly the 88 `[Font Styles]` size fields doubled (verified by field-masked diff: 88 differing lines, all size-only; CRLF preserved; ASCII only).

## Test plan (when ready — game files untouched so far)

1. Copy `FontStyle.candidate.ini` → `C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\FontStyle.ini`.
2. Launch; menus/tooltips/puck text should be visibly ~2x. If unsure it was picked up: Process Monitor, filter Path contains `FontStyle.ini` — expect probes of `...\Plugins\FontStyle.ini` then `...\SimCity 4 Deluxe\FontStyle.ini` (SUCCESS).
3. Sweep: main menu, region view, city view (puck, RCI, tooltips, query), budget, graphs, news ticker (expected unchanged), load screen, in-world signs.
4. Revert = delete the file (stock behavior returns via DBPF fallback). Per-style revert = copy that line back from `FontStyle.default.ini`.

## Confidence and top risks

**Confidence: HIGH** that the loose file is read from the two locations above (direct disassembly of the shipped 1.1.641 exe, corroborated by string cluster `Font Styles` / `Font Aliases` / `FontStyle.ini` / `Arta` and the file-exists helper). **MEDIUM** on the full visual outcome — the loose path is engine-supported but community-untested; the parser is the same one used for the DBPF copy, so format risk is minimal.

Top risks:
1. News ticker/news panels ignore size (known from the DAT precedent) — partial coverage, not a crash.
2. Overflow in elements the window-doubler doesn't grow (fixed-width number boxes; community saw this) — cosmetic, fix per style.
3. World-anchored styles (`Signpost`, `Label`) doubling when they shouldn't — revert those lines if so.
4. An eventual plugin dropping `Plugins\FontStyle.ini` would silently shadow ours — keep root as the only copy and remember the priority order.

## Sources

- Binary analysis: `C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe` (string at VA 0xA86DC8; font init at 0x44db60; details above) and `Apps\SimCity 4.ini`.
- Default table extracted from `SimCity_1.dat` (TGI `0x00000000,0x4A87BFE8,0x2A87BFFC`, QFS-compressed).
- Font Table format: https://wiki.sc4devotion.com/index.php?title=Font_Table (SC4D Encyclopaedia, copied from SimsWiki) — matches the Maxis in-file spec verbatim.
- INI overview / TGI list: https://wiki.sc4devotion.com/index.php?title=INI
- cISC4App vtable order: https://github.com/nsgomez/gzcom-dll (gzcom-dll/include/cISC4App.h)
- Precedent mod: https://community.simtropolis.com/files/file/30826-increase-font-size/ (via search snippets; page gated)
- Related thread: https://community.simtropolis.com/forums/topic/760505-font-size-adjustment/ (gated)
- Checked, no info: https://www.sc4devotion.com/forums/index.php?topic=13344.0 ; https://www.pcgamingwiki.com/wiki/SimCity_4 (no font/UI-scale content)
