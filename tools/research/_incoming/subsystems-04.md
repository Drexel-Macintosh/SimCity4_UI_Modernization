# TARGET: PRIMARY: `tools\research\SC4-UI-ENGINE.md` — §3 "The `.UI` script format". Insert §3.0a (lexical contract) immediately after the §3.1 census; replace the two "one element per line" sentences in §3.1; correct the "14 `winflag_*`" count in §3.1; append new §3.7–§3.12 after §3.6. Add 8 rows to §8.2's VA table. Add items 14–16 to §9 (contradictions).
SECONDARY: `tools\uiscripts\UISCRIPTS.md` — replace the "## Format" paragraph (line 34) and the "Attribute survey" paragraph (lines 60–65) with a pointer to the new §3.7–§3.9; the census tables and the `imagerect`/art analysis stand unchanged.
TERTIARY: `tools\research\METHOD.md` — one paragraph under the string-scan guidance (the pooled-literal / NULL-IS-NOT-EVIDENCE lesson in §3.8 below).

## SUMMARY
Recovered the complete `.UI` grammar from the loader itself rather than from the corpus: SimCity 4.exe contains six keyword-registration tables (391 attribute/value keywords) plus a tag table (14 tokens), all interning name→token-id into the dictionary singleton at `[0x00B63588]`. Every one of the 192 attributes used by the 281 shipped scripts is in that dictionary — nothing in the corpus is a typo or a dead attribute — and the dictionary also names 199 keywords the corpus never uses, including `pos=`/`size=` as an alternative to `area=`, `imagetype=`, `alpha=` on GZWinBMP, `blttype=divider|bluebar`, the `<define>/<name>/<val>` tag set, and three entire widget classes (GZWinLineInput, GZWinFileBrowser, GZWinTextTicker). Two operationally load-bearing discoveries: (1) the stock `font=4888` / `font=0x00001318` tokens are the loader's own id for the keyword `default` (registration `push 0x1318; push 0xAD63FC` at `0x00955823`), and no such FontStyle GUID exists in either font table — which sharpens §3.4 and contradicts its `[OPEN]` note; (2) the "one element per line" rule in both docs is false — 107 elements across 23 files carry newlines inside quoted values, and 84 quoted values in 19 files contain a literal `>`, which is exactly what `build_selective_safe.py`'s two `<LEGACY[^>]*>` regexes assume cannot happen. Also produced the full 192-row attribute frequency table, the per-class attribute matrix, the complete 21-file multi-root list (§3.6 lists 6, and its "NINE" My Sims roots enumerate only eight ids — the ninth is `0xABB26B0E`), and the builder-coverage gap: 11 pixel-valued attributes in the statically-scaled set that neither generator scales, plus two windows whose `gutters=` exceed the byte range the SDK setter declares once doubled.

## CONTRADICTIONS
- SC4-UI-ENGINE.md §3.4's `[OPEN]` says some font style NAMES resolve (`DataInsetHeader` works, `RegionLabel`/`RegionPopulation`/`Mayor*`/`PUckDate` do not) and nominates the `<LEGACY>` tag handler at 0x94B995 as the suspect. MEASURED: the tokenizer dictionary is a fixed 391-keyword grammar table built by six registration functions and contains ZERO FontStyle style names (positive control: grammar words `default`, `center`, `standard` ARE present); and 0x94B995 is the `LEGACY` string's own registration site inside the 14-entry TAG table, not a handler. Also, the obvious 'different class' escape is closed — `DataInsetHeader` (x5) and `RegionLabel` (x1) are both on plain GZWinText. So no style name can resolve via the token path, which contradicts the observation that DataInsetHeader works. The [OPEN] must stay open; the tag handler is ruled out.
- UISCRIPTS.md line 34 ("Text, one pseudo-XML element per line") and SC4-UI-ENGINE.md §3.1 ("one pseudo-XML `<LEGACY …>` element per line") are both false. MEASURED: 107 of 5,964 elements span multiple physical lines across 23 files, because quoted `tiptext`/`caption` values contain raw newlines. Demonstrated by the delta between a line-based and a quote-aware tokenizer on the same corpus: tipoffsets 1,959 -> 2,066; tipflag 1,959 -> 2,066; tipres 876 -> 983; btnclicksnd 1,317 -> 1,422; align 3,723 -> 3,830.
- UISCRIPTS.md line 61 and SC4-UI-ENGINE.md §3.1 both say "14 `winflag_*`". MEASURED: there are 13 winflag_* names, 11 of them on 100% of elements (5,964) and two near-universal (winflag_acceptfocus 5,852, winflag_alphablend 5,845). The exe's base keyword table at 0x0094D641 registers exactly 13 (0xF01A..0xF026). No fourteenth name exists in the corpus or the exe.
- SC4-UI-ENGINE.md §3.6 says My Sims `I-aa1f1f57` "has NINE" roots but enumerates only eight ids. MEASURED: the ninth top-level root is `0xABB26B0E` (present in src\UiSpike.cpp, GOD-MODE-FLYOUTS.md and MAYOR-MODE.md, absent from §3.6's list). §3.6 also lists six multi-root scripts; the corpus contains 21.
- SC4-UI-ENGINE.md §3.3 and UISCRIPTS.md describe `imagerect` as the blanket-2x breaker and note there is 'no inset/edges/corners/slice attribute anywhere in the corpus' — both correct — but the exe registers a base attribute `imagetype` (token 0xF017, string @0x00AD5590) that sits between `image` and `imagerect` in the same block and is used ZERO times in the corpus. Its semantics are unmeasured; it is a plausible per-image draw-mode selector and should not be assumed nonexistent just because no shipped script uses it.
- A latent conflict between build_selective_safe.py and the corpus: `double_subtree_areas` (lines 489 and 537) matches `<LEGACY[^>]*>`, which assumes no `>` inside a tag. MEASURED: 84 quoted values in 19 files contain a literal `>` (e.g. caption="<alignment target>" in the live HUD script I-2bc90671, caption="<Data Map Type>" x10 in the live Data Views script I-2bc9060f). POSITIVE CONTROL: the 49 files that function actually edits (advisor, budget, Graphs, and the 43 `id=0x4bcb938a` dashboards) have empty intersection with those 19, so it has never fired — but the safety margin is accidental.

## OPEN
- Does the `.UI` gutters setter truncate to a byte? vendor\gzcom-dll declares cIGZWinGen::SetGutters(uint8_t,uint8_t) / (int8_t x4), cIGZWinText::SetGutters(int8_t,int8_t), cIGZWinBtn::SetGutters(uint8_t,...). The stock corpus reaches gutters=(247,201) on GZWinGen root 0x2A57CB84 (I-8a7e052f, Graphic Options) and (232,232) on 0xCA5E6261 (I-aa5e60d1) — BOTH inside build_dialog_static.py's scaled set, so the shipped 2x package writes (494,402) and (464,464). Cheapest test: dump GetGutters on 0x2A57CB84 in the deployed 2x build. (494,402) = no ceiling; (238,146) = truncation, and those two roots need a clamp (and a general clamp for any future tier > 1x on values above 127).
- What does `imagetype=` (base token 0xF017) do? Registered between `image` and `imagerect`, zero corpus uses. If it selects a per-image draw mode it may be a cheaper lever than the GZWinBMP Plot hook for the runtime-image cases (task #47).
- What do `blttype=divider` and `blttype=bluebar` draw? Registered as GZWinGen tokens 65538/65539 alongside `edge`/`tiled`/`normal`, zero corpus uses. Two undocumented frame modes that a third-party .UI could ship.
- Do `pos=(x,y)` + `size=(w,h)` behave identically to `area=`? Registered as base tokens 0x0102/0x0103 with parse-side `(%d,%d)` support, zero corpus uses, and `size` has only its own registration as a code reference (the serializer never writes it). Every geometry regex we own keys on `area=` and would scale nothing on such a script — worth a guard/warning in both builders even before the semantics are pinned.
- Which registered attributes are parsed-but-inert? All 391 keywords are interned to token ids, but only §3.4's string-valued `font=` (property 0xFAA4AE85, zero consumers) is PROVEN inert. Establishing this per attribute means following each token to a setter; do not assume any other attribute is ignored without that trace.
- Should `gutters`/`textoffsets` scale at runtime? SC4UIScale.dll has no gutter setter call site (positive control: 10 SetArea/SetSize/SetPosition sites in the same files), so every runtime-swept window keeps 1x padding while the 163 statically-doubled scripts get scaled padding. This is an untested axis for the stock-parity work (tasks #31/#70) and for the born-2x subtrees of §3.6, whose children get doubled area= but 1x gutters=.
- Close the 11-value builder gap: scrollbargutters (3), buttongutter (3), combodownarrowrect (3), icongutter (1), minmaxboxsize (1) in the statically-scaled set. combodownarrowrect=(0,0,64,15) in I-0a243d80 / I-e9263de5 / I-e9a56248 is the only one with a visible consequence (1x drop-arrow rect inside a doubled combo).

---

# For `tools\research\SC4-UI-ENGINE.md` §3

---

## §3.1 — three corrections in place

Replace *"one pseudo-XML `<LEGACY …>` element per line"* with *"one
pseudo-XML `<LEGACY …>` element per record; records are usually one line
but a quoted value may contain raw newlines"* (see §3.0a).

Replace *"every control has `clsid`, `area`, `fillcolor`, 14 `winflag_*`"*
with *"every control has `clsid`, `area`, `fillcolor` and **11** universal
`winflag_*`; two more (`winflag_acceptfocus`, `winflag_alphablend`) are
near-universal. There are **13** `winflag_*` names in total, not 14."*

> **EVIDENCE (MEASURED, corpus)** — quote-aware scan of the 281 text layout
> scripts in `tools\uiscripts\extracted\`: 5,964 `<LEGACY>` elements.
> `winflag_visible / _enabled / _moveable / _sizeable / _sortable / _pbuff /
> _pbufftrans / _pbufferase / _pbuffvid / _mousetrans / _ignoremouse` = 5,964
> each (100%); `winflag_acceptfocus` = 5,852; `winflag_alphablend` = 5,845.
> No fourteenth `winflag_*` name exists in the corpus **or** in the exe.
> **EVIDENCE (MEASURED, exe)** — the base keyword table at `0x0094D641`
> registers exactly 13: `winflag_visible` (`0xF01A`) … `winflag_acceptfocus`
> (`0xF025`), `winflag_alphablend` (`0xF026`).

Add to the census line: **5,964 elements, 884 `<CHILDREN>`/`</CHILDREN>`
pairs, 329 top-level roots, 192 distinct attributes, 36 distinct `clsid`
values, 17 distinct `iid` values, 4,215 `id=` attributes over 1,408 distinct
ids.** 1,749 elements (29%) carry **no `id=` at all**.

---

## §3.0a THE LEXICAL CONTRACT — what a `.UI` parser must survive

⛔ **`.UI` is not line-oriented. A parser that splits on newlines is wrong,
and a regex of the form `<LEGACY[^>]*>` is wrong.** Four hazards, each with
its measured population:

1. **Quoted values contain raw newlines.** 107 of the 5,964 elements (1.8%)
   span more than one physical line, across 23 files. Everything *after* the
   embedded newline — typically `tipres`, `tipoffsets`, `tipflag`, `align`,
   `btnclicksnd` — is invisible to a line-based reader.
   > **EVIDENCE (MEASURED)** — a line-based tokenizer and a quote-aware one
   > over the same corpus disagree by exactly 107 on every attribute that
   > follows a long `tiptext`: `tipoffsets` 1,959 → **2,066**, `tipflag`
   > 1,959 → **2,066**, `tipres` 876 → **983**, `btnclicksnd` 1,317 →
   > **1,422**, `align` 3,723 → **3,830**. Worst files:
   > `I-2bc90671` / `I-898897de` (10 elements each), `I-c9930681` and
   > `I-e99237ff` (6 each).

2. **A literal `>` occurs inside quoted values.** 84 occurrences in 19 files —
   placeholder captions such as `caption="<alignment target>"` (the HUD
   script `I-2bc90671`), `caption="<Data Map Type>"` (×10 in each of the three
   Data Views copies, including the **live** `I-2bc9060f`),
   `caption="<Sim Name>"` / `"<MySim Name>"` (19 in My Sims `I-aa1f1f57`),
   and `caption="Add ->"` in `I-49bffbfe`.
   > **EVIDENCE (MEASURED)** — full list of the 19 files is reproducible with
   > a quote-aware scan; counts per file: `aa1f1f57` 19, `0b72f276` /
   > `2bc9060f` / `ea287193` 10 each, `0a243d80` and `8aa9aa14` 2 each, the
   > rest 1.

3. **One file carries a UTF-8 BOM.** `T-00000000_G-96a006b0_I-ca551016.ui`
   (the **Credits** script, and a `build_dialog_static.py` target) begins
   `EF BB BF # Generated by UI editor`. A parser that tests `text[0] == '#'`
   or `startswith('#')` treats its header as content.
   > **EVIDENCE (MEASURED)** — 280 of 281 files start with `#`; this one
   > starts with the BOM.

4. **Backslash escapes exist for `'` but not for `"`.** The corpus contains
   `station\'s` (`I-c9930681`) but **zero** `\"` sequences, which is the only
   reason a naive quote-toggle scanner works today.
   > **EVIDENCE (MEASURED)** — 0 of 5,964 elements contain `\"`. This is a
   > structural null with its positive control: the same scan finds 84 bare
   > `>` and the `\'` occurrences, so it *could* have seen `\"`.

**The one invariant you may rely on: the attribute PREFIX order.** Every
element begins `clsid`, then `iid` (if present), then `id=` (if present),
then `area=` — and `caption=` never precedes any of them.

> **EVIDENCE (MEASURED)** — first-three-attribute signature over all 5,964
> elements: `(clsid, iid, id)` 4,209; `(clsid, iid, area)` 1,749;
> `(clsid, id, area)` 6 (the six elements that omit `iid`). Elements where
> `clsid`/`iid`/`id`/`area` appears **after** `caption`: **0**.
> Beyond that prefix the order is *not* fixed — 86 attribute pairs occur in
> both orders somewhere in the corpus (mostly `font`/`forecolor`/`bkgcolor`
> versus the `winflag_*` block, which differs by class).

This invariant is why the `[^>]*` regexes in `build_selective_safe.py` have
not yet corrupted anything (§3.12), and it is exactly the property a
third-party `.UI` generator is under no obligation to preserve.

---

## §3.7 THE TAG GRAMMAR — bigger than `<LEGACY>` and `<CHILDREN>`

The loader registers **14 tag keywords** into the same dictionary it uses for
attributes, through a different vtable slot (`[vt+0x24]` for tags,
`[vt+0x0C]` for attributes):

| token id | spellings | in corpus |
|---|---|---|
| `0` | `_null`, `none` | no |
| `1` | `children`, `_children` | yes (884) |
| `2` | `/children`, `_/children` | yes (884) |
| `3` | `define`, `_define` | **no** |
| `4` | `name`, `_name` | **no** |
| `5` | `val`, `_val` | **no** |
| `0xFA450242` | `LEGACY` | yes (5,964) |
| `0x12` / `0x13` | `comic9`, `comic10` | no (legacy font faces in the same table) |

> **EVIDENCE (MEASURED, exe 1.1.641.0, ImageBase `0x400000`,
> file offset = VA − `0x400000`)** — registration function
> `0x0094B740`–`0x0094BA20`. Sites: `_null` @`0x0094B777`,
> `_children` @`0x0094B7A6`, `_/children` @`0x0094B7D1`,
> `_define` @`0x0094B7FC`, `_name` @`0x0094B827`, `_val` @`0x0094B852`,
> `none` @`0x0094B88F`, `children` @`0x0094B8BA`, `/children` @`0x0094B8E5`,
> `define` @`0x0094B910`, `name` @`0x0094B93B`, `val` @`0x0094B966`,
> `LEGACY` @`0x0094B994` (`push 0xFA450242; push 0xAD5194`),
> `comic9` @`0x0094B9BF`, `comic10` @`0x0094B9EA`. Each site is the pattern
> `push <id>; push <cstr>; lea ecx,[ebp-0x18]; call 0x00408480;
> mov ecx,[0x00B63588]; push eax; call [reg+0x24]` — `0x00408480` is a
> GZString-from-`char*` constructor (visible `strlen` loop at
> `0x004084A5`–`0x004084AA`).

This closes §8.2's parenthetical "(the unproven tokenizer suspect)" for
`0x0094B995`: that address is the `LEGACY` **registration** inside the tag
table, not a handler.

⛔ **`<define>` / `<name>` / `<val>` are a real, unexercised sub-language.**
No shipped script uses them, so their semantics are unmeasured — but a
third-party `.UI` may, and our parsers would silently drop the whole
construct. `<_children>` is an accepted synonym for `<CHILDREN>` and our
parsers do not recognise it.

---

## §3.8 THE KEYWORD DICTIONARY — 391 names, six tables, one id space

The `.UI` loader does **not** strcmp attribute names at parse time. Six
registration functions intern every grammar word — attribute names **and**
enum values, in the same namespace — into the dictionary singleton at
`[0x00B63588]`. The parse result handed to each class deserializer is an
array of 8-byte `[tokenId][value*]` pairs.

| VA range | pairs | scope | id block |
|---|---|---|---|
| `0x0094D641`–`0x0094E33A` | 64 | base window + booleans | `0x0100`, `0xF000` |
| `0x0095127E`–`0x0095404D` | 177 | FlatRect, Text, TextEdit, ListBox, Combo, Btn, BMP, Slider, Scrollbar, LineInput, Spinner, Outline, Gen, TextTicker, Folders, Custom | `0x0200`–`0x1200`, `0x10000` |
| `0x009552D3`–`0x009560B0` | 68 | GZWinFileBrowser | `0x1300` |
| `0x00957C9D`–`0x009580EE` | 21 | GZWinOptGrp | `0x0F00` |
| `0x009599E7`–`0x00959E04` | 20 | GZWinTreeView | `0x1400` |
| `0x0095B036`–`0x0095B897` | 41 | GZWinGrid | `0x1600` |

The mirror-image **serializer** bands are `0x0095C23C`–`0x009613BE` (195
sites), `0x00962973`–`0x00964031`, `0x00964694`–`0x00964B0A` and
`0x009658BC`–`0x00965C94` — this is the round-trip writer §8.2 records at
`0x0095BC5F`.

**Booleans have three spellings each.** `yes` = `true` = `on` = 1;
`no` = `false` = `off` = 0.
> **EVIDENCE (MEASURED)** — base table: `push 1; push "yes"` @`0x0094D6BC`,
> `push 1; push "true"` @`0x0094D6ED`, `push 0; push "no"` @`0x0094D71D`,
> `push 0; push "false"` @`0x0094D74D`, plus `on`/`off`. The corpus uses only
> `yes`/`no`, and for `toggle`/`triggerondown` only `on`/`off`.

**Base window attribute ids** (`0x0094D641` table, the ones every class
inherits):

`clsid` −1 · `iid` −2 · `id` `0x0100` · `area` `0x0101` · **`pos` `0x0102`** ·
**`size` `0x0103`** · `fillcolor` `0x0104` · `caption` `0x0105` ·
`captionres` `0x0106` · `transparent` `0x0107` · `comments` `0x0108` …
`commentskd` `0x010F` · `font` `0xF000` · `bkgcolor` `0xF001` ·
`forecolor` `0xF002` · `notify` `0xF003` · `gutters` `0xF004` ·
`style` `0xF005` · *(enum values sharing the id space)* `left` `0xF006`,
`right` `0xF007`, `center` `0xF008`, `flat` `0xF009`, `normal` `0xF00A`,
`sunken` `0xF00B`, `raised` `0xF00C`, `fill` `0xF00D`, `nofill` `0xF00E` ·
`colorfontnormal` `0xF00F` … `colorfonthilitedbkg` `0xF014` ·
`align` `0xF015` · `image` `0xF016` · **`imagetype` `0xF017`** ·
`imagerect` `0xF018` · `outline` `0xF019` · `winflag_visible` `0xF01A` …
`winflag_alphablend` `0xF026`.

⛔ **`pos=(x,y)` + `size=(w,h)` is a legal alternative to `area=`.** It is
registered (`0x0102` @`0x0094D8B3` region, `0x0103`), the parse-side format
strings `(%d,%d)` (`0xAD542C`) exist, and the corpus uses it **zero** times —
so **every geometry regex we own keys on `area=` and would silently scale
nothing on a script that uses `pos`/`size`.** `size` has exactly two 32-bit
references in the image, one of which is its own registration, so the
serializer never *writes* it: it is parse-only, and therefore invisible to
anyone who studies only shipped data.

**Keywords the loader knows that the corpus never uses (199 of 391).** The
operationally interesting ones:

| keyword | class block | note |
|---|---|---|
| `pos`, `size` | base | alternative geometry, see above |
| `imagetype` | base | sits between `image` and `imagerect`; semantics unmeasured |
| `transparent` | base | distinct from GZWinBMP's `transparentbkg` |
| `dbgdrawarea`, `autofit` | GZWinText | a **debug** area-outline flag and an auto-fit flag |
| `alpha` | GZWinBMP `0x0B00` | the third BMP attribute; corpus uses only `transparentbkg`, `edgeimage` |
| `divider`, `bluebar` | GZWinGen | two `blttype=` modes beyond `edge`/`tiled`/`normal` |
| `radio`, `noimage`, `standardhilite`, `standardhilitefixed`, `togglebtnfixed`, `standardfixed` | GZWinBtn `style=` | six unused button styles |
| `all`, `lrb`, `trb`, `top`, `bottom` | GZWinFlatRect `style=` | corpus uses only `nofill`, `bottom` |
| `leftbottom`, `rightbottom` | `align=` | the two unused corners of the 9 |
| `notifyonreturn`, `notifyonchange`, `notifyonlostfocus`, `enableclipboard`, `passwordmode`, `hscrollimage(Rect)`, `vscrollimage(Rect)` | GZWinTextEdit | |
| `setlinevisible`, `setlineontop` | GZWinListBox | |
| `combodownarrowimage` | GZWinCombo | |
| `wingridrow`, `wingridcell`, `enablehdr` | GZWinGrid | the row/cell twins of `wingridcol` |
| `coloroutline` | GZWinSpinner | the unsuffixed form of the four we do see |
| `rooticon`, `rooticonselected`, `rooticonexpanded`, `rooticonexpandedselected` | GZWinTreeView | |
| whole class | `GZWinLineInput` (`0x0E00`, 12 attrs), `GZWinFileBrowser` (`0x1300`, 66 attrs), `GZWinTextTicker` (`0x1200`: `speed`, `frequency`, `message`), `SC3WinGen` | three widget classes and one legacy alias with zero corpus instances |

⛔ **A string scan of the exe under-reports this vocabulary — do not use one
as an existence test.** The keyword literals are spread across at least seven
pools and shared with unrelated subsystems, so scanning the obvious
`0xAD5000`–`0xAD7100` block "proves" that `id`, `caption`, `align`, `image`,
`option`, `sort`, `userdata`, `winflag_visible` and `winflag_enabled` are
absent. They are not: `id` @`0x00A81394`, `caption` @`0x00A8138C`,
`image` @`0x00A844A8`, `winflag_enabled` @`0x00A863C4`,
`winflag_visible` @`0x00A863D8`, `left` @`0x00AA1BD8`,
`right` @`0x00AA1BCC`, `size` @`0x00A9F59C`, and `align` @`0x00A9F524`
**shared with the particle-effect keyword table** (its neighbours are
`collide`, `model`, `texture`, `randomWalk`). *The registration tables are
the authority; a string scan is not.* (This is the string-scan form of the
NULL-IS-NOT-EVIDENCE law and belongs in `METHOD.md` as well.)

**Nothing in the shipped corpus is a dead attribute.** All 192 attribute
names used by the 281 scripts appear in the dictionary, and all 247 candidate
names tested have at least one 32-bit reference in the image.
> **EVIDENCE (MEASURED)** — set difference of the corpus attribute list
> against the six registration tables: empty.

---

## §3.9 `font=4888` IS `font=default` — and what that does to §3.4

Two numeric `font=` values appear in the **stock** corpus: `font=4888` (45
occurrences) and `font=0x00001318` (14). **They are the same token** —
`0x1318` = 4888 — and that token is the loader's own id for the keyword
**`default`**.

> **EVIDENCE (MEASURED, exe)** — `0x00955823: push 0x1318` /
> `0x00955828: push 0xAD63FC` / `0x0095582D: lea ecx,[ebp-0x24]` /
> `0x00955830: call 0x00408480` / `0x00955835: mov ecx,[0x00B63588]` /
> `0x0095583B: push eax` / `0x0095583C: call [edi+0x0C]`. The string at
> `0x00AD63FC` is `"default"` (the GZWinFileBrowser sort/column keyword,
> block `0x13`, index `0x18`).
> **EVIDENCE (MEASURED, corpus)** — the two spellings occur on `GZWinBtn`
> (43 + 12), `GZWinText` (1 + 2) and `GZWinSpinner` (1), in 20 files
> including `I-e9923283`, `I-c9930681`, `I-e99237ff`, `I-aa356502`,
> `I-ebd0d36c` and both `I-09923283` twins. Several are on the
> `id=0x0000AAAA` alignment markers.

**No FontStyle GUID `0x1318` exists.** So whichever way the `GZWinText`
handler at `0x0094E516` reads it — as token `default`, or as a GUID via
`SetFontStyleByGUID` — it lands on the `GetStyleByGUID` fallback
`0x68963C4C` "Default" that §3.4 already documents.

> **EVIDENCE (MEASURED)** — `tools\fonts\FontStyle.default.ini` is
> **byte-identical** to the in-`.dat` font table
> `T-00000000_G-4a87bfe8_I-2a87bffc.ui` (22,396 bytes, SHA-1
> `ba9126b409d5…`). Neither contains `1318` or `4888`; both contain 92 lines
> carrying 8-hex-digit GUIDs. **Positive control:** the same search finds
> `GenBodyMedium` in both files, so it would have found `0x00001318`.

**Operational consequence for both builders.** `font=4888` and
`font=0x00001318` are already in the numeric form §3.4 prescribes, and both
generators correctly leave them alone —
`build_selective_safe.py:270` uses `FONT_NAME_RE = font=([A-Za-z][A-Za-z0-9_]*)`,
which requires a leading letter. Keep that anchor; a `\w+` there would rewrite
`4888` into a bogus GUID.

**What this does NOT resolve.** The dictionary contains **zero** FontStyle
style names — `GenBodyMedium`, `PUckDate`, `DataInsetHeader`, `RegionLabel`
are all absent while grammar words like `default`, `center`, `standard` are
present — so **no** style name can reach a font through the token path. That
contradicts §3.4's `[OPEN]` note that `DataInsetHeader` resolves while
`RegionLabel` does not, and the obvious escape (different class) is closed:
both are on plain `GZWinText` (`DataInsetHeader` ×5, `RegionLabel` ×1). See
§9 item 14.

---

## §3.10 THE VALUE GRAMMAR — nine shapes, from the serializer's own templates

The round-trip writer's `printf` templates in `.rdata` enumerate every value
shape the format has:

| template | VA | shape |
|---|---|---|
| `%s=%d ` | `0x00AD6E2C` | integer |
| `%s=0x%08x ` | `0x00AD6E34` | hex integer (the `font=0x........` writer) |
| `%s=%s ` | `0x00AD6E70` | bare token |
| `%s="%s" ` | `0x00AD6E78` | quoted string |
| `%s=(%d,%d) ` | `0x00AD6E50` | 2-tuple |
| `%s=(%d,%d,%d,%d) ` | `0x00AD6E5C` | 4-tuple |
| `%s=(%u,%u,%u) ` | `0x00AD6DD0` | RGB triple |
| `%s=(%u,%u,%u)(%u,%u,%u) ` | `0x00AD6DE0` | 2 × RGB |
| `%s={%08x,%08x} ` | `0x00AD6E40` | `{group,instance}` |
| `%s="%u:%s:%u::" ` | `0x00AD6E84` | OptGrp `option` |
| `%s="%u:%s:%u:{%08x,%08x}:(%d,%d,%d,%d)" ` | `0x00AD6E98` | OptGrp long form |
| `%s="%u:(%d,%d)" ` | `0x00AD6EC4` | `optionmoveto` / `optionsetsize` |
| — | `0x00AD5418` | parse side: `{%x,%x}` — `image=` is scanf'd with `%x`, so `0x`-prefixing and case are both tolerated |
| — | `0x00AD6884`, `0x00AD6890` | parse side: `%d,%d,%d` and `%08x,%08x` (grid cell specs) |

⛔ **Four tuple-valued attributes are NOT pixels.** `minmax=(lo,hi)` and
`stepsize` (GZWinSpinner), `minmaxvalue=(lo,hi)` (GZWinSlider,
GZWinScrollbar), `linepagecount=(32,32)` (GZWinScrollbar) and
`insertpos=(0,0)` (GZWinTextEdit) are **value ranges and caret state**.
`maxtext`, `maxundo`, `caretperiod`, `charlimit` are counts. Every
`*color*`/`fillcolor`/`colorleft…` value is an RGB triple. A "scale every
`(a,b)`" transform corrupts all of them; both current builders are safe only
because their regexes are name-anchored.

**Elementary value tallies worth knowing:**
`blttype` = `edge` 277 / `tiled` 254 / `normal` 9 (only on `GZWinGen` and
`0x89e1567c`, 540 total) · `style` = `standard` 1,432 / `radiocheck` 251 /
`label` 233 / `nofill` 216 / `toggle` 150 / `bottom` 29 / `flat` 1 ·
`align` = `center` 2,113 / `lefttop` 589 / `leftcenter` 533 / `righttop` 297 /
`rightcenter` 136 / `left` 106 / `right` 37 / `centertop` 17 /
`centerbottom` 2 · `edgeimage` = `no` 788 / `yes` 56 · `tipflag` =
`0x01000000` 2,063 / `0x00020000` 3 · `textoffsets` and `tipoffsets` are
`(0,0)` in **all** 1,733 / 2,066 occurrences · `notify=no`, `userdata=0`,
`triggerondown=off`, `tipsdelay=no`, `tipstimeout=no`, `paint=yes`,
`sidebar=no`, `gobackvisible=no`, `minmaxvisible=no`, `hscrollbar=no`,
`caretcolor=(0,0,0)`, `caretperiod=1000`, `overwrite=no`, `insertindex=0`,
`insertpos=(0,0)`, `colhdrsz=0`, `rowhdrsz=0` are **constant** across the
whole corpus.

---

## §3.11 THE ATTRIBUTE FREQUENCY TABLE — so the tail is visible

All 192 attributes, quote-aware, over 5,964 elements / 281 files.

**Universal (5,964 = every element):** `clsid`, `area`, `fillcolor`, and the
11 universal `winflag_*`.
**Near-universal:** `iid` 5,958 (279 files) · `winflag_acceptfocus` 5,852 ·
`winflag_alphablend` 5,845.

**Common (>500):** `gutters` 4,520 · `id` 4,215 · `align` 3,830 ·
`image` 2,962 · `caption` 2,696 · `font` 2,668 · `fill` 2,637 ·
`notify` 2,578 · `style` 2,312 · `colorfontnormal`/`colorfontdisabled`/
`colorfonthilited` 2,223 each · `colorfontnormalbkg`/`colorfontdisabledbkg`/
`colorfonthilitedbkg` 2,172 each · `toggle`/`triggerondown`/`showcaption`/
`autosize`/`wrapcaption`/`shiftcaption`/`tips`/`tipsdelay`/`tipstimeout`/
`tiptext`/`tipoffsets`/`tipflag` 2,066 each (= every GZWinBtn) ·
`wrapped`/`opaque` 1,845 · `captionres` 1,777 · `forecolor`/`bkgcolor` 1,734 ·
`textoffsets` 1,733 · `btnclicksnd` 1,422 · `tipres` 983 ·
`transparentbkg` 845 · `edgeimage` 844 · `imagerect` 839 · `outline` 694 ·
`blttype`/`userdata`/`moveable`/`sizeable`/`defaultkeys`/`closevisible`/
`gobackvisible`/`minmaxvisible`/`closedisabled`/`gobackdisabled`/
`minmaxdisabled`/`titlebar`/`paint`/`sidebar` 540 each (= every GZWinGen +
`0x89e1567c`).

**Mid (100–500):** `colorleft`/`colortop`/`colorright`/`colorbottom` 277 ·
`initvalue` 163 · `highlightcolor` 127 · `hscrollbar`/`vscrollbar` 122 ·
`editable` 116 · the 13 GZWinTextEdit-only attributes 112 each
(`caretvisible`, `allowinsert`, `allowundo`, `singleline`, `caretcolor`,
`maxtext`, `overwrite`, `insertindex`, `insertpos`, `caretperiod`, `maxundo`)
· `outlinecolor` 105.

**THE RARE TAIL — the part that surprises people (each with its file set):**

| n | files | attribute(s) |
|---|---|---|
| 49 | 15 | `btnupsnd` |
| 31 | 5 | `autonumber`, `autonumbercomma`, `autonumbercurrency`, `minmax`, `stepsize`, `coloroutlinel/t/r/b`, `digits` — GZWinSpinner only (`I-49d55c68`, `I-6bc61f19`, `I-aa3acdfe`, `I-cbc3c2b9`, `I-e9263d4d`) |
| 23 | 20 | the whole **GZWinGrid** vocabulary: `fontcolor`, `textalign`, `textwrapping`, `selrule`, `maxselcount`, `olinecolor`, `dcolwidth`, `drowheight`, `colhdrsz`, `rowhdrsz`, `fnone`, `fedit`, `fhscroll`, `fvscroll`, `fcolheading`, `frowheading`, `fcolgrid`, `frowgrid`, `finsmode`, `fopqbkgnd`, `fdoutline`, `fdgridoutline`, `fcellwrap`, `fallownosel`, `ffixcolcnt`, `ffixrowcnt`, `fdpastlastcol`, `fdpastlastrow`, `fcelloverlap`, `fdrpdnmenu`, `fhlcelldata`, `fdefault`, `fall`, `colgridclr`, `rowgridclr` |
| 21 | 17 | `minmaxvalue`, `direction` (GZWinSlider) |
| 18 | 15 | `wingridcol` |
| 15 | 11 | `initselection` |
| 10 | 7 | `scrollbargutters`, `sort`, `drop`, `sunken` (GZWinListBox) |
| 10 | 3 | `comments`, `commentslmd`, `commentsrmd`, `commentslmu`, `commentsrmu`, `commentsmm`, `commentsku`, `commentskd` — all `""`, editor scratch |
| 4 | 3 | `combodownarrowrect`, `combodowncolor`, `buttongutter`, `listelement` (GZWinCombo: `I-0a243d80`, `I-e9263de5`, `I-e9a56248`) |
| **1** | **1** | `colordark`, `colorlight`, `node` (GZWinOutline, `I-49d55c68`) · `maincaption`, `itemcaption`, `drawfill`, `labelfontcolornormal`, `labelfontcolordisabled`, `buttonfontcolornormal`, `buttonfontcolorhilited`, `buttonfontcolordisabled`, `autofilltype`, `option`, `optionmoveto`, `optionsetsize` (the corpus's **single GZWinOptGrp**, `I-49d55c68`) · `displayroot`, `displaynodeicons`, `displaytreelines`, `multiselect`, `icongutter`, `rowheight`, `minmaxboxsize`, `backgroundcolor`, `roottext`, `rootcolorforeground`, `rootcolorbackground`, `rootcolorforegroundhilited`, `rootcolorbackgroundhilited`, `rootfont`, `rootexpanded`, `rootselected` (the **single GZWinTreeView**, `I-8a5ab1cd` = City Import) · `pagesize`, `linesize`, `linepagecount` (the **single GZWinScrollbar**, `I-ebd0d36c` = Select A Bridge) · `defcolor` (one GZWinText) |

**Per-class attribute matrix** — the one structural fact it reveals:

⛔ **Every custom (hex-`clsid`) class writes ONLY base-window attributes.**
`0xCBCBF1E0` (134 uses), `0xCA318388` (48), `0xCA1492AC` (12),
`0xC7A0E17E` (12), `0xAA5C2F86` (12), `0xAA12E5F5` (5), `0x28C5A41F` (3) and
the nine singletons carry no class-specific attribute at all. A `.UI` script
literally *cannot* say anything about a custom widget beyond geometry, art
ref and flags — which is the data-side explanation for why the §2 catalogue
finds TrendBar, RCI, AdviceList and the minimap all code-bound.

**The one exception is `0xAA7CECFD`, and it is informative.** It carries
`wrapped` / `opaque` / `textoffsets` — the GZWinText attribute set — and every
one of its 56 instances declares `iid=IGZWinText`. **`0xAA7CECFD` is a
GZWinText subclass**, which extends §2's catalogue row (currently "unnamed in
the registry … resolves fonts independently of the GZWinText name path") with
a data-side reason.

More generally, `iid=` is redundant and optional: all 5,958 present values are
exactly `I` + the class name, six elements omit it entirely with no ill
effect, and the hex clsids declare their **base interface** —
`0x89E1567C` → `IGZWinGen`; `0xAA7CECFD` → `IGZWinText`; `0xCBCBF1E0`,
`0xCA318388`, `0xCA1492AC`, `0xC7A0E17E`, `0xAA5C2F86`, `0xAA12E5F5` and the
rest → `IGZWinCustom`.

**Defaults.** The loader's per-attribute defaults were **not** measured here —
proving them requires following each token to its setter. What *is* measured
is the omission law: **attribute omission in this corpus is per-FILE, never
per-element.** The 14 files that omit `winflag_acceptfocus` and the 16 that
omit `winflag_alphablend` omit them on **100%** of their elements
(`I-e9a56248` 35/35, `I-e9263d4d` 23/23, `I-891c9259` 7/7, …). Those two
attributes also carry the two highest base ids (`0xF025`, `0xF026`) and are
registered out of source order — i.e. they were added late, and those files
were last saved by an older UI editor. Treat "attribute missing" as an
editor-version signature, not as a meaningful per-control choice.

---

## §3.6 — corrections and the complete multi-root list

§3.6's principle stands; its enumeration is incomplete in two ways.

**(a) There are 21 multi-root scripts, not six.** 329 top-level roots across
281 files; 260 files have one root, 12 have two, 4 have three, 2 have four,
1 has seven, 2 have nine. Maximum `<CHILDREN>` nesting depth is **4** (98
files reach depth 1, 116 depth 2, 63 depth 3, 4 depth 4).

| roots | script | root ids |
|---|---|---|
| 9 | `I-aa1f1f57` (both groups) | `0x698894D3`, `0xCA1F1D9C`, `0xEA1F1E4D`, `0xAA1F1EC5`, `0x6A61E29F`, `0xABBAA2D3`, `0xEA1F1E4E`, `0xEA1F1E5E`, **`0xABB26B0E`** |
| 7 | `I-aa920991` | `0x6A91DC14`, `0xEA8CAD19`, `0x09EBE9EE`, `0x09EBEE60`, `0x09EBEE45`, `0x6A91DC16`, `0x6A91DC15` |
| 4 | `I-aa3acdfe`, `I-cbc3c2b9` | `0xAA3AC002`, `0xCA4C332D`, `0xAA3AC001`, `0xAA3AC000` |
| 3 | `I-4a160034`, `I-cbc905cd` | `0x6A15C767`, `0xAA15EF06`, `0x2A1D96B1` |
| 3 | `I-6bc9065a`, `I-ea2871aa` | `0x8A8B5B71`, `0x8A8B5B72`, `0x0A4A8176` |
| 2 | `I-2a2aed99` (both groups) | `0xCA2AEDC0`, **`0xAA231508`** |
| 2 | `I-2bc90671`, `I-898897de` (both groups) | `0xE9889775`, `0x69E40A1F` |
| 2 | `I-c973b411` (both groups) | `0x0987B48F`, `0xEA8CAD14` |
| 2 | `I-0bfac164` | `0x6BFAC122`, `0x8BFAC13E` |
| 2 | `I-abfac197` | `0xCBFACAE1`, `0x8BFAC13E` |
| 2 | `I-6a9455c9` | `0x27DF05BF`, `0x27DF05BE` |
| 2 | `I-abc0ed33` | `0x0BB0F5E7`, `0x6BB92BCA` |

**(b) The My Sims "NINE" enumerates only eight ids.** The ninth is
`0xABB26B0E` — present in `UiSpike.cpp` and in `GOD-MODE-FLYOUTS.md` /
`MAYOR-MODE.md`, but not in §3.6's list, which is exactly the reading path
someone would take when applying the "deferral must cover the whole
composition" law.

Two entries deserve a callout because they touch shipped fixes:
`I-6a9455c9` (Obliterate City) has **two** roots and
`build_dialog_static.py`'s TARGETS comment records only `0x27df05be`;
`I-2a2aed99` (news ticker) has a second root `0xAA231508` alongside the
marquee host that `build_selective_safe.py` special-cases.

---

## §3.12 OPERATIONAL — what our generators rewrite, and where the edges are

**The two builders partition the corpus with zero overlap.**
`build_selective_safe.py` stages **88** scripts; `build_dialog_static.py`
stages **163**; the intersection is **empty**, and together they cover 251 of
the 281 layout scripts.
> **EVIDENCE (MEASURED)** — TGI sets of `tools\selective-safe\stage\*.ui` and
> `tools\dialog-static\stage\*.ui`.

| attribute | corpus | selective-safe | dialog-static |
|---|---|---|---|
| `area` | 5,964 | **only** inside named subtrees + the ticker marquee width | **scaled, every node** |
| `imagerect` | 839 | scaled iff that control's art went 2x | scaled iff that control's art went 2x |
| `image` `{g,i}` | 2,962 | retargeted to clone TGI | retargeted to clone TGI |
| `font=NAME` | 2,668 | → GUID hex (numeric tokens skipped) | → GUID hex (numeric tokens skipped) |
| `gutters` | 4,520 | not touched (by design — runtime sweep owns geometry) | **scaled** |
| `textoffsets`, `tipoffsets` | 1,733 / 2,066 | not touched | **scaled** (both are always `(0,0)`, so the edit is a no-op today) |
| `d?rowheight`, `d?colwidth`, `rowhdrsz`, `colhdrsz` | 23 each | n/a | **scaled** |
| `wingridcol` width slot (every 3rd) | 18 | n/a | **scaled** |

**Safe to rewrite:** `area`, `imagerect`, `image`, `font`, `gutters`,
`textoffsets`, `tipoffsets`, `d?rowheight`, `d?colwidth`, `rowhdrsz`,
`colhdrsz`, the third slot of each `wingridcol` triple.
**Never rewrite:** any `id=0x0000AAAA` marker's `area` (§6.1 — both builders
already skip it), `minmax`, `minmaxvalue`, `stepsize`, `linepagecount`,
`insertpos`, `maxtext`, `maxundo`, `charlimit`, and the first two slots of a
`wingridcol` triple (indices, not pixels).

**Residual gap — 11 pixel values in the statically-scaled set that neither
builder scales:** `scrollbargutters` (3), `buttongutter` (3),
`combodownarrowrect` (3), `icongutter` (1), `minmaxboxsize` (1) inside
`build_dialog_static.py`'s 163 scripts; `scrollbargutters` ×4 inside
selective-safe's 88. The one with visible consequence is
`combodownarrowrect=(0,0,64,15)` — a 64×15 drop-arrow rect left at 1x inside
a doubled GZWinCombo, in `I-0a243d80` (Select A My Sim), `I-e9263de5` and
`I-e9a56248`.

**⛔ THE `[^>]*` TRAP.** `build_selective_safe.py`'s `double_subtree_areas`
uses `re.search(r"<LEGACY[^>]*\sid=0x%s\b[^>]*>")` at line 489 and
`re.sub(r"<LEGACY[^>]*>", rep_tag, …)` at line 537. Neither is quote-aware,
and 84 quoted values in the corpus contain `>` (§3.0a).
> **EVIDENCE (MEASURED, and this is the positive control the null needs):**
> the function is applied to `I-cbc905cd` / `I-4a160034` (advisor strip),
> `I-aa3acdfe` / `I-cbc3c2b9` (budget), `I-6bc9065a` / `I-ea2871aa` (Graphs)
> and the **43** scripts containing `id=0x4bcb938a` (U-Drive-It dashboards).
> Intersection of that 49-file set with the 19 `>`-bearing files: **empty**.
> So this has never fired — and it survives even on intersection only
> because `id=` and `area=` always precede `caption=` (§3.0a). **A
> third-party `.UI` under no such ordering obligation breaks it silently.**
> Fix is one line: reuse the quote-aware `parse_ui()` already in the same
> file instead of the two regexes.

**⛔ CLIENT PADDING NEVER SCALES AT RUNTIME.** `SC4UIScale.dll` contains no
`SetGutters` / `SetTextOffsets` / `SetTipPlacementOffsets` call site, so
every window the runtime sweep doubles keeps **1x padding**; only the 163
statically-doubled dialog scripts carry scaled padding.
> **EVIDENCE (MEASURED)** — grep of `src\UiSpike.cpp` + `src\CodePatches.cpp`
> for `SetGutter|Gutter\(|TextOffset|TipOffset`: zero call sites (the single
> hit at `UiSpike.cpp:8620` is a comment). **Positive control:** the same
> files contain 10 `SetArea`/`SetSize`/`SetPosition` call sites, so the grep
> could have found a setter.
> This is a candidate contributor to residual stock-parity deltas (tasks #31,
> #70) and to the born-2x subtrees of §3.6 (advisor / budget / Graphs /
> dashboard), whose children get doubled `area=` but 1x `gutters=`.

**⚠ BYTE-RANGE CEILING ON `gutters` (HYPOTHESIS — verify before acting).**
The vendor SDK declares the gutter setters as 8-bit:
`cIGZWinGen::SetGutters(uint8_t,uint8_t)` and the 4-arg
`SetGutters(int8_t,int8_t,int8_t,int8_t)` (`vendor\gzcom-dll\gzcom-dll\include\cIGZWinGen.h:67,70`),
`cIGZWinBtn::SetGutters(uint8_t,…)` (`cIGZWinBtn.h:102,104`),
`cIGZWinText::SetGutters(int8_t,int8_t)` and
`SetTextOffsets(int8_t,int8_t)` (`cIGZWinText.h:66,69`),
`cIGZWinOptGrp` / `cIGZWinSpinner` `uint8_t`, `cIGZWinCombo::SetBtnGutter(int8_t)`.
The stock corpus contains gutter components up to **247**:

| script | class | window | `gutters` | builder |
|---|---|---|---|---|
| `I-8a7e052f` (Graphic Options) | GZWinGen | `0x2A57CB84` | `(247,201)` | **dialog-static — scaled** |
| `I-aa5e60d1` | GZWinGen | `0xCA5E6261` | `(232,232)` | **dialog-static — scaled** |
| `I-abc0ed33` | GZWinGen | `0x0BB0F5E7` | `(232,232)` | selective-safe (not scaled) |
| `I-aa3acdfe`, `I-cbc3c2b9` | `0x89E1567C` | `0xAA3AC002`, `0xCA4C332D` | `(226,98)`, `(228,154)` | selective-safe (not scaled) |

At ×2 the builder writes `(494,402)` and `(464,464)`; if the setter truncates
to a byte those land at `(238,146)` and `(208,208)` — the first is *smaller*
than the 1x value on one axis. **Not proven at the call site**: the SDK
header is a community reconstruction and the deserializer's actual setter
call was not disassembled. **Cheapest verification:** in the deployed 2x
build, dump `GetGutters` on `0x2A57CB84` — `(494,402)` means no truncation,
`(238,146)` means the ceiling is real and the two dialog-static roots need a
clamp. `textoffsets` and `tipoffsets` are unaffected (always `(0,0)`;
`SetTipPlacementOffsets` is `int32_t` anyway).

**Parser model, for anyone writing a third generator.** The deserializer
receives an array of 8-byte `[tokenId][value*]` records and scans it for its
own token ids; the value object's `[vt+0x0C]` returns a **type code**, where
**type 6 = interned token** (this is the "type 6" §3.4 refers to).
> **EVIDENCE (MEASURED)** — `0x0094E38D: lea eax,[eax+ecx*8]` /
> `0x0094E390: cmp dword ptr [eax], 0xF005` (= `style`) /
> `0x0094E39C: mov eax,[eax+4]` / `0x0094E3AB: call [edx+0x0C]` /
> `0x0094E3AE: cmp eax, 6` / `0x0094E383: mov ebx, 0xF006` (= `left`,
> the base of the `style` enum range `0xF006`–`0xF00E`).

---

# For §8.2's VA table — eight new rows

| VA | What |
|---|---|
| `0x00408480` | GZString-from-`char*` ctor used by every keyword registration (`strlen` loop @`0x004084A5`) |
| `[0x00B63588]` | the **keyword dictionary singleton**; attributes register through `[vt+0x0C]`, tags through `[vt+0x24]` |
| `0x0094B740`–`0x0094BA20` | **tag keyword table** (14: `LEGACY` `0xFA450242`, `children` 1, `/children` 2, `define` 3, `name` 4, `val` 5, `null`/`none` 0, `_`-prefixed synonyms, `comic9`/`comic10`). `0x0094B995` is the `LEGACY` registration, **not** a handler |
| `0x0094D641`–`0x0094E33A` | **base attribute table**, 64 pairs — `id` `0x0100`, `area` `0x0101`, `pos` `0x0102`, `size` `0x0103`, `font` `0xF000` … `winflag_alphablend` `0xF026`; boolean synonyms `yes`/`true`/`on`=1, `no`/`false`/`off`=0 |
| `0x0095127E`–`0x0095404D` | per-class attribute tables, 177 pairs (FlatRect `0x02xx` … TextTicker `0x12xx`, GZWinGen `0x10000+`) |
| `0x009552D3`–`0x009560B0`; `0x00957C9D`–`0x009580EE`; `0x009599E7`–`0x00959E04`; `0x0095B036`–`0x0095B897` | FileBrowser `0x13xx` (68) / OptGrp `0x0Fxx` (21) / TreeView `0x14xx` (20) / Grid `0x16xx` (41) tables |
| `0x00955823` / `0x00AD63FC` | registration of token **`0x1318` = 4888 = `"default"`** — the identity of the stock `font=4888` / `font=0x00001318` |
| `0x0094E38D`–`0x0094E3AE` | the attribute-record walk: 8-byte `[tokenId][value*]`, `[vt+0x0C]` type code, **type 6 = token** |
| `0x00AD6DD0`–`0x00AD6EC4` | the serializer's 12 value-format templates (§3.10) |

---

# For §9 — three new contradictions

14. **Can a `font=` style NAME ever resolve?** §3.4's `[OPEN]` records that
    `DataInsetHeader` works while `RegionLabel`, `RegionPopulation`,
    `Mayor*` and `PUckDate` do not, and nominates the `<LEGACY>` tag handler
    as the suspect. The tokenizer is now fully enumerated — 391 grammar
    keywords in six tables (§3.8) — and it contains **zero** FontStyle style
    names, so the token path cannot resolve *any* of them; and the "different
    class" escape is closed because `DataInsetHeader` (×5) and `RegionLabel`
    (×1) are both on plain `GZWinText`. **Unresolved by evidence.** The
    `[OPEN]` must stay open, but the tag handler is now ruled out as the
    mechanism. The operational rule (§3.4: always ship `font=0x........`) is
    unaffected and is now *more* strongly motivated.
15. **"One element per line."** `UISCRIPTS.md` line 34 and §3.1 both state it;
    107 elements in 23 files disprove it, and the difference shows up as
    ~107-count deltas on every attribute that follows a long `tiptext`
    (§3.0a). **Resolution: records, not lines.**
16. **"14 `winflag_*`."** Both `UISCRIPTS.md` (line 61) and §3.1 say 14. The
    corpus has 13 names (11 universal + 2 near-universal) and the exe
    registers exactly 13. **Resolution: 13.**
