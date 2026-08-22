# Selective 2x UI-Art Override Packages

Built 2026-07-21 from the full 2x-upscaled art set at `tools\upscale\preview\SimCity_1\`
(2,206 PNGs, TypeID 0x856DDBAC) using `tools\dbpf\DbpfPack.exe`. Each package overrides
ONLY the PNG resources of one GroupID (or the mirror pair), so any research verdict about
which groups serve which game screens (city HUD vs region screen vs menus) can be served
instantly by deploying just the matching .dat(s).

All packages verified: `DbpfPack.exe --list` entry count == staged file count, and every
listed entry's GroupID matches the package's group(s). Zero staging failures.

## Group inventory (from upscale\preview\SimCity_1 filenames)

| GroupID    | Files in upscale set | Source PNGs (extracted-png-tgi.csv) | Package |
|------------|---------------------:|------------------------------------:|---------|
| 0x46a006b0 |                  784 |                                 810 | yes |
| 0x1abe787d |                  743 |                                 743 | yes |
| 0x6a386d26 |                  356 |                                 356 | yes |
| 0x4c06f888 |                  112 |                                 112 | yes |
| 0xab7e5421 |                   93 |                                  93 | yes |
| 0x00000001 |                   62 |                                  62 | yes |
| 0x22dec92d |                   39 |                                  39 | yes |
| 0x6a1eed2c |                   13 |                                  20 | yes |
| 0xa9179251 |                    0 (4 below threshold) |                4 | no (under 5-file threshold) |
| 0xca133ecb |                    0 |                                  41 | no (absent from upscale set) |
| **Total**  |            **2,206** |                           **2,280** | |

Note: the upscale set covers 2,206 of the 2,280 source PNGs. The 74 not covered
(26 of 0x46a006b0, all 41 of 0xca133ecb, 7 of 0x6a1eed2c) are simply not present in any
package; the game falls back to the original art for those TGIs. Overrides are per-TGI,
so partial coverage inside a group is safe.

## Packages

| Package | Entries | Size (bytes) |
|---------|--------:|-------------:|
| z_SC4UIScale_Art_2x_G0x46a006b0.dat |   784 | 14,544,896 |
| z_SC4UIScale_Art_2x_G0x1abe787d.dat |   743 | 12,673,339 |
| z_SC4UIScale_Art_2x_G0x6a386d26.dat |   356 |  4,993,394 |
| z_SC4UIScale_Art_2x_G0x4c06f888.dat |   112 |    467,830 |
| z_SC4UIScale_Art_2x_G0xab7e5421.dat |    93 |    261,742 |
| z_SC4UIScale_Art_2x_G0x00000001.dat |    62 |    619,895 |
| z_SC4UIScale_Art_2x_G0x22dec92d.dat |    39 |    177,954 |
| z_SC4UIScale_Art_2x_G0x6a1eed2c.dat |    13 |    620,594 |
| z_SC4UIScale_Art_2x_MirrorPair.dat  | 1,527 | 27,218,139 |
| **Total (all 9)** | | **61,577,783** |

`z_SC4UIScale_Art_2x_MirrorPair.dat` = the two near-identical groups 0x46a006b0 + 0x1abe787d
combined (784 + 743 entries). Deploy it INSTEAD of those two per-group packages, not alongside
them (alongside is harmless but redundant).

## Deploying

Copy the chosen .dat file(s) to:

    %USERPROFILE%\Documents\SimCity 4\Plugins\

SC4 loads plugin .dat files in alphabetical order and the LAST loader wins per TGI, so the
override file must sort late — the `z_` prefix already ensures that. Mix and match any subset
of packages; each touches only its own group's resources. To revert, delete the .dat(s) from
Plugins (originals in SimCity_1.dat are untouched).

Rebuild recipe (if the upscale set changes): stage one group's PNGs
(`*_G-0x########_*.png`) into an empty folder, then
`dbpf\DbpfPack.exe <stageDir> selective\z_SC4UIScale_Art_2x_G0x########.dat`
and confirm `--list` entry count matches the staged count.
