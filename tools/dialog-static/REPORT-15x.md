# Region-screen dialogs -- static 1.5x (`z_SC4UIScale_DialogStatic-15x.dat`)

Built 2026-08-30 by `build_dialog_static.py`. STANDALONE package: the game creates each
of the 164 region-screen dialogs/popups already doubled from an edited copy of its
.UI script and lays out the children itself. No runtime scaling involved; runtime
docking of the region-dialog roots must stay disabled while testing. The recipe is
the one user-VALIDATED in-game on the Load Region dialog (2026-07-21) and then on
the six-dialog dat; the previously shipped scripts are re-emitted UNCHANGED through
the same pipeline, so everything lives in this one dat, which REPLACES the earlier
dat of the same name.

| Dialog | Script TGI (T/G/I) | Root window |
|---|---|---|
| Move In My Sim marker (green+red, #191) | `0x00000000 / 0x96A006B0 / 0x6A9455C9` | 0x89e1567c id=0x27df05bf, 1x 46x97 |
| Play Options | `0x00000000 / 0x96A006B0 / 0x0A7DF315` | GZWinGen id=0x2a57db82, 1x 699x523 |
| Audio Options | `0x00000000 / 0x96A006B0 / 0xCA53F06E` | GZWinGen id=0xea53f5db, 1x 330x471 |
| Graphic Options | `0x00000000 / 0x96A006B0 / 0x8A7E052F` | GZWinGen id=0x2a57cb82, 1x 722x558 |
| Region Name (Create Region) | `0x00000000 / 0x96A006B0 / 0x8A5AB1CB` | GZWinGen id=0xea5ba0d1, 1x 330x168 |
| Delete Region confirm | `0x00000000 / 0x96A006B0 / 0x8A5AB1CE` | GZWinGen id=0x6a5ba20c, 1x 300x158 |
| Load Region | `0x00000000 / 0x96A006B0 / 0x8A5AB1CC` | GZWinGen id=0x4a5ba0e7, 1x 330x188 |
| Quit confirm (region screen) | `0x00000000 / 0x96A006B0 / 0x4A551B4C` | GZWinGen id=0xaa921f4f, 1x 330x109 |
| Quit confirm (are-you-sure) | `0x00000000 / 0x96A006B0 / 0x8A5AB1CF` | GZWinGen id=(no id), 1x 313x128 |
| Start New City bubble | `0x00000000 / 0x96A006B0 / 0x0A8CD184` | 0x89e1567c id=0x0a551c50, 1x 216x165 |
| Existing-city bubble | `0x00000000 / 0x96A006B0 / 0xCA539340` | 0x89e1567c id=0x0a551c50, 1x 258x250 |
| Photo Album | `0x00000000 / 0x96A006B0 / 0x4A8CC5EA` | GZWinGen id=0x0a8cd3ee, 1x 683x582 |
| Delete City confirm | `0x00000000 / 0x96A006B0 / 0x8A5AB1D0` | GZWinGen id=0x8a5ab1d0, 1x 302x128 |
| City Import | `0x00000000 / 0x96A006B0 / 0x8A5AB1CD` | GZWinGen id=0x0a5ba192, 1x 330x188 |
| Generic message box (code-driven confirms) | `0x00000000 / 0x96A006B0 / 0xEA8CC3C6` | GZWinGen id=0x8a8dfcf5, 1x 364x192 |
| Credits | `0x00000000 / 0x96A006B0 / 0xCA551016` | GZWinGen id=0x0a592004, 1x 525x284 |
| Advisor toast (salmon) | `0x00000000 / 0x96A006B0 / 0x4A5A89D4` | GZWinGen id=0x4a9db60c, 1x 450x246 |
| Advisor toast (salmon B) | `0x00000000 / 0x96A006B0 / 0x4A5A89D5` | GZWinGen id=0x4a9db60c, 1x 450x246 |
| Advisor toast (green) | `0x00000000 / 0x96A006B0 / 0x2BB16D50` | GZWinGen id=0xebb16d71, 1x 450x246 |
| Advisor toast (blue) | `0x00000000 / 0x96A006B0 / 0x0BBC06B6` | GZWinGen id=0xebbc081e, 1x 450x246 |
| Advisor toast (peach) | `0x00000000 / 0x96A006B0 / 0x4BBC080F` | GZWinGen id=0xebbc081e, 1x 450x246 |
| Building query (residential) | `0x00000000 / 0x96A006B0 / 0xCA56783A` | GZWinGen id=0x10000005, 1x 292x334 |
| Building query (tall variant) | `0x00000000 / 0x96A006B0 / 0x4A5672BF` | GZWinGen id=0x10000005, 1x 292x443 |
| Building query (short variant) | `0x00000000 / 0x96A006B0 / 0x2A567DC1` | GZWinGen id=0x10000005, 1x 292x336 |
| Obliterate City confirm | `0x00000000 / 0x96A006B0 / 0x2A41436C` | GZWinGen id=0x27df05be, 1x 339x200 |
| Reconcile Edges (boundaries match) | `0x00000000 / 0x96A006B0 / 0x0A4D0C43` | GZWinGen id=0x6a4d0a59, 1x 357x152 |
| Reconcile Edges (highlighted areas confirm) | `0x00000000 / 0x96A006B0 / 0xCA4D0B22` | GZWinGen id=0x6a4d0a59, 1x 357x157 |
| Reconcile Edges (variant 3) | `0x00000000 / 0x96A006B0 / 0x8A4D0A17` | GZWinGen id=0x6a4d0a59, 1x 357x182 |
| Exit to Region confirm (in-city, 3-btn) | `0x00000000 / 0x96A006B0 / 0x6A553AA4` | GZWinGen id=0xaa921f4f, 1x 270x161 |
| Quit confirm (in-city, 3-btn) | `0x00000000 / 0x96A006B0 / 0x0A55161D` | GZWinGen id=0xaa921f4f, 1x 330x157 |
| Exit to Region (in-city, play-city variant) | `0x00000000 / 0x96A006B0 / 0xEAAEEC1B` | GZWinGen id=0x6aaeec4a, 1x 330x157 |
| Can't-save-during-disaster confirm | `0x00000000 / 0x96A006B0 / 0x4A89B3F2` | GZWinGen id=0x2a96ed21, 1x 300x128 |
| Establish City | `0x00000000 / 0x96A006B0 / 0x2A41436B` | GZWinGen id=0x6a414973, 1x 434x234 |
| Select A My Sim (Sim-mode sim picker) | `0x00000000 / 0x96A006B0 / 0x0A243D80` | GZWinGen id=0x6a243d9e, 1x 434x381 |
| U-Drive-It Select vehicle for <MySim> | `0x00000000 / 0x96A006B0 / 0x4BF325E8` | GZWinGen id=0xcbf32603, 1x 434x447 |
| U-Drive-It Select pedestrian style | `0x00000000 / 0x96A006B0 / 0xABFAEF15` | GZWinGen id=0xcbf32603, 1x 434x299 |
| Missing plugin-packs warning (city load) | `0x00000000 / 0x96A006B0 / 0xEA89B6C3` | GZWinGen id=0x2a5cfb2c, 1x 355x238 |
| Generic one-button notification popup | `0x00000000 / 0x96A006B0 / 0xCA8CBF0F` | GZWinGen id=0xaa8def97, 1x 300x166 |
| Select A Bridge (network across water) | `0x00000000 / 0x96A006B0 / 0xEBD0D36C` | GZWinGen id=0x0c525b9e, 1x 411x371 |
| Tutorial page (also an HTML-fed pane - see list D) | `0x00000000 / 0x96A006B0 / 0x0A2DD355` | GZWinGen id=0x4a35b0f2, 1x 473x308 |
| Tutorial exit confirm | `0x00000000 / 0x96A006B0 / 0x6A5E73C0` | GZWinGen id=0xea5e748c, 1x 330x113 |
| Game Over / Run for Senator | `0x00000000 / 0x96A006B0 / 0x0A5CF71D` | GZWinGen id=0x2a5cfb2c, 1x 355x218 |
| Startup splash 768x600 | `0x00000000 / 0x96A006B0 / 0x8AA9AA14` | GZWinGen id=0xaaa9c9d9, 1x 768x600 |
| Startup splash 800x600 | `0x00000000 / 0x96A006B0 / 0xAAAAF3D1` | GZWinGen id=0xaaa9c9d9, 1x 800x600 |
| Clock time popup | `0x00000000 / 0x96A006B0 / 0xAA5E60D1` | GZWinGen id=0xca5e6261, 1x 92x30 |
| Label Tool (map annotation) | `0x00000000 / 0x96A006B0 / 0x6B704690` | GZWinGen id=0x8a8dfcf5, 1x 409x142 |
| Region city-bubble stub (narrow) | `0x00000000 / 0x96A006B0 / 0xCA539343` | GZWinGen id=0x0a551c53, 1x 42x159 |
| Select A Bridge sibling button | `0x00000000 / 0x96A006B0 / 0xEBD0D36D` | GZWinGen id=0x000a0000, 1x 89x58 |
| Text Entry prompt (Save City confirm) | `0x00000000 / 0x96A006B0 / 0xE9263D4C` | GZWinGen id=0xc9264be2, 1x 319x113 |
| Set Lot Size | `0x00000000 / 0x96A006B0 / 0xE9263DE5` | GZWinGen id=0x8926eebe, 1x 249x92 |
| Query panel 0a562a05 | `0x00000000 / 0x96A006B0 / 0x0A562A05` | GZWinGen id=0x10000005, 1x 292x120 |
| Query panel 0a8b819e | `0x00000000 / 0x96A006B0 / 0x0A8B819E` | GZWinGen id=0x10000005, 1x 292x203 |
| Query panel 0a8b98fe | `0x00000000 / 0x96A006B0 / 0x0A8B98FE` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 0a8b9a67 | `0x00000000 / 0x96A006B0 / 0x0A8B9A67` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 0a8b9c43 | `0x00000000 / 0x96A006B0 / 0x0A8B9C43` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 0a8b9c6a | `0x00000000 / 0x96A006B0 / 0x0A8B9C6A` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 0c1d56e4 | `0x00000000 / 0x96A006B0 / 0x0C1D56E4` | 0x89e1567c id=0x10000006, 1x 212x410 |
| Query panel 0c1d730b | `0x00000000 / 0x96A006B0 / 0x0C1D730B` | 0x89e1567c id=0x10000006, 1x 212x375 |
| Query panel 0c1d7737 | `0x00000000 / 0x96A006B0 / 0x0C1D7737` | 0x89e1567c id=0x10000006, 1x 212x320 |
| Query panel 0c1d7974 | `0x00000000 / 0x96A006B0 / 0x0C1D7974` | 0x89e1567c id=0x10000006, 1x 212x305 |
| Query panel 0c1d79ac | `0x00000000 / 0x96A006B0 / 0x0C1D79AC` | 0x89e1567c id=0x10000006, 1x 212x300 |
| Query panel 0c1d7b60 | `0x00000000 / 0x96A006B0 / 0x0C1D7B60` | 0x89e1567c id=0x10000006, 1x 212x340 |
| Query panel 0c1d7e71 | `0x00000000 / 0x96A006B0 / 0x0C1D7E71` | 0x89e1567c id=0x10000006, 1x 212x370 |
| Query panel 0c1d81fc | `0x00000000 / 0x96A006B0 / 0x0C1D81FC` | 0x89e1567c id=0x10000006, 1x 212x350 |
| Query panel 2a554f6d | `0x00000000 / 0x96A006B0 / 0x2A554F6D` | GZWinGen id=0x10000005, 1x 292x284 |
| Query panel 2a5621ee | `0x00000000 / 0x96A006B0 / 0x2A5621EE` | GZWinGen id=0x10000005, 1x 292x181 |
| Query panel 2a564884 | `0x00000000 / 0x96A006B0 / 0x2A564884` | GZWinGen id=0x10000005, 1x 292x225 |
| Query panel 2a56675c | `0x00000000 / 0x96A006B0 / 0x2A56675C` | GZWinGen id=0x10000005, 1x 292x138 |
| Query panel 2a5e7490 | `0x00000000 / 0x96A006B0 / 0x2A5E7490` | GZWinGen id=0x10000005, 1x 502x213 |
| Query panel 2a8b7e1c | `0x00000000 / 0x96A006B0 / 0x2A8B7E1C` | GZWinGen id=0x10000005, 1x 292x242 |
| Query panel 2a8b97c1 | `0x00000000 / 0x96A006B0 / 0x2A8B97C1` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 2a8b99d0 | `0x00000000 / 0x96A006B0 / 0x2A8B99D0` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 2a8b9df2 | `0x00000000 / 0x96A006B0 / 0x2A8B9DF2` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 2c02ba84 | `0x00000000 / 0x96A006B0 / 0x2C02BA84` | 0x89e1567c id=0x10000006, 1x 216x136 |
| Query panel 2c096de6 | `0x00000000 / 0x96A006B0 / 0x2C096DE6` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 2c1d73cb | `0x00000000 / 0x96A006B0 / 0x2C1D73CB` | 0x89e1567c id=0x10000006, 1x 212x325 |
| Query panel 2c1d784b | `0x00000000 / 0x96A006B0 / 0x2C1D784B` | 0x89e1567c id=0x10000006, 1x 212x325 |
| Query panel 2c1d8024 | `0x00000000 / 0x96A006B0 / 0x2C1D8024` | 0x89e1567c id=0x10000006, 1x 212x320 |
| Query panel 4a562da5 | `0x00000000 / 0x96A006B0 / 0x4A562DA5` | GZWinGen id=0x10000005, 1x 292x205 |
| Query panel 4a565d13 | `0x00000000 / 0x96A006B0 / 0x4A565D13` | GZWinGen id=0x10000005, 1x 292x211 |
| Query panel 4a5665eb | `0x00000000 / 0x96A006B0 / 0x4A5665EB` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 4a566c14 | `0x00000000 / 0x96A006B0 / 0x4A566C14` | GZWinGen id=0x10000005, 1x 292x205 |
| Query panel 4a566d6e | `0x00000000 / 0x96A006B0 / 0x4A566D6E` | GZWinGen id=0x10000005, 1x 292x210 |
| Query panel 4a5e7ed3 | `0x00000000 / 0x96A006B0 / 0x4A5E7ED3` | GZWinGen id=0x10000005, 1x 502x172 |
| Query panel 4a8b7fe7 | `0x00000000 / 0x96A006B0 / 0x4A8B7FE7` | GZWinGen id=0x10000005, 1x 292x242 |
| Query panel 4a8b9396 | `0x00000000 / 0x96A006B0 / 0x4A8B9396` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 4a8b9936 | `0x00000000 / 0x96A006B0 / 0x4A8B9936` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 4a8b9c92 | `0x00000000 / 0x96A006B0 / 0x4A8B9C92` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 4a8b9dab | `0x00000000 / 0x96A006B0 / 0x4A8B9DAB` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 4c0969e2 | `0x00000000 / 0x96A006B0 / 0x4C0969E2` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 4c1a68d2 | `0x00000000 / 0x96A006B0 / 0x4C1A68D2` | 0x89e1567c id=0x10000006, 1x 212x345 |
| Query panel 4c1d78f7 | `0x00000000 / 0x96A006B0 / 0x4C1D78F7` | 0x89e1567c id=0x10000006, 1x 212x330 |
| Query panel 4c1d7c0c | `0x00000000 / 0x96A006B0 / 0x4C1D7C0C` | 0x89e1567c id=0x10000006, 1x 212x320 |
| Query panel 4c1d7c65 | `0x00000000 / 0x96A006B0 / 0x4C1D7C65` | 0x89e1567c id=0x10000006, 1x 212x355 |
| Query panel 4c1d7d40 | `0x00000000 / 0x96A006B0 / 0x4C1D7D40` | 0x89e1567c id=0x10000006, 1x 212x350 |
| Query panel 4c47800e | `0x00000000 / 0x96A006B0 / 0x4C47800E` | GZWinGen id=0x10000005, 1x 292x221 |
| Query panel 6a51506f | `0x00000000 / 0x96A006B0 / 0x6A51506F` | GZWinGen id=0x10000005, 1x 292x210 |
| Query panel 6a555a84 | `0x00000000 / 0x96A006B0 / 0x6A555A84` | GZWinGen id=0x10000005, 1x 292x221 |
| Query panel 6a561b3a | `0x00000000 / 0x96A006B0 / 0x6A561B3A` | GZWinGen id=0x10000005, 1x 292x223 |
| Query panel 6a562f56 | `0x00000000 / 0x96A006B0 / 0x6A562F56` | GZWinGen id=0x10000005, 1x 292x283 |
| Query panel 6a566151 | `0x00000000 / 0x96A006B0 / 0x6A566151` | GZWinGen id=0x10000005, 1x 292x221 |
| Query panel 6a8b9875 | `0x00000000 / 0x96A006B0 / 0x6A8B9875` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 6a8b9acc | `0x00000000 / 0x96A006B0 / 0x6A8B9ACC` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 6a8b9af3 | `0x00000000 / 0x96A006B0 / 0x6A8B9AF3` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 6c1d789a | `0x00000000 / 0x96A006B0 / 0x6C1D789A` | 0x89e1567c id=0x10000006, 1x 212x340 |
| Query panel 6c1d7ac3 | `0x00000000 / 0x96A006B0 / 0x6C1D7AC3` | 0x89e1567c id=0x10000006, 1x 212x340 |
| Query panel 6c1d7f5c | `0x00000000 / 0x96A006B0 / 0x6C1D7F5C` | 0x89e1567c id=0x10000006, 1x 212x305 |
| Query panel 6c1d8057 | `0x00000000 / 0x96A006B0 / 0x6C1D8057` | 0x89e1567c id=0x10000006, 1x 212x320 |
| Query panel 8a554483 | `0x00000000 / 0x96A006B0 / 0x8A554483` | GZWinGen id=0x10000005, 1x 292x274 |
| Query panel 8a5e7bd2 | `0x00000000 / 0x96A006B0 / 0x8A5E7BD2` | GZWinGen id=0x10000005, 1x 502x213 |
| Query panel 8a8b95b0 | `0x00000000 / 0x96A006B0 / 0x8A8B95B0` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 8a8b9811 | `0x00000000 / 0x96A006B0 / 0x8A8B9811` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 8a8b98a7 | `0x00000000 / 0x96A006B0 / 0x8A8B98A7` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 8a8b9d12 | `0x00000000 / 0x96A006B0 / 0x8A8B9D12` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel 8a948d49 | `0x00000000 / 0x96A006B0 / 0x8A948D49` | GZWinGen id=0x10000005, 1x 292x144 |
| Query panel 8c1d7423 | `0x00000000 / 0x96A006B0 / 0x8C1D7423` | 0x89e1567c id=0x10000006, 1x 212x353 |
| Query panel 8c1d76d5 | `0x00000000 / 0x96A006B0 / 0x8C1D76D5` | 0x89e1567c id=0x10000006, 1x 212x300 |
| Query panel 8c3bd047 | `0x00000000 / 0x96A006B0 / 0x8C3BD047` | 0x89e1567c id=0x10000006, 1x 212x320 |
| Query panel aa554aea | `0x00000000 / 0x96A006B0 / 0xAA554AEA` | GZWinGen id=0x10000005, 1x 292x229 |
| Query panel aa555346 | `0x00000000 / 0x96A006B0 / 0xAA555346` | GZWinGen id=0x10000005, 1x 292x182 |
| Query panel aa561f93 | `0x00000000 / 0x96A006B0 / 0xAA561F93` | GZWinGen id=0x10000005, 1x 292x160 |
| Query panel aa565036 | `0x00000000 / 0x96A006B0 / 0xAA565036` | GZWinGen id=0x10000005, 1x 292x210 |
| Query panel aa565f5b | `0x00000000 / 0x96A006B0 / 0xAA565F5B` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel aa5661eb | `0x00000000 / 0x96A006B0 / 0xAA5661EB` | GZWinGen id=0x10000005, 1x 292x211 |
| Query panel aa5bef41 | `0x00000000 / 0x96A006B0 / 0xAA5BEF41` | GZWinGen id=0x10000005, 1x 292x165 |
| Query panel aa5e14cc | `0x00000000 / 0x96A006B0 / 0xAA5E14CC` | GZWinGen id=0x10000005, 1x 502x214 |
| Query panel aa8b9755 | `0x00000000 / 0x96A006B0 / 0xAA8B9755` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel aa8b9971 | `0x00000000 / 0x96A006B0 / 0xAA8B9971` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel aa8b999e | `0x00000000 / 0x96A006B0 / 0xAA8B999E` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel ac096ac7 | `0x00000000 / 0x96A006B0 / 0xAC096AC7` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel ac1d544d | `0x00000000 / 0x96A006B0 / 0xAC1D544D` | 0x89e1567c id=0x10000006, 1x 212x325 |
| Query panel ac1d7548 | `0x00000000 / 0x96A006B0 / 0xAC1D7548` | 0x89e1567c id=0x10000006, 1x 212x375 |
| Query panel ac1d7a81 | `0x00000000 / 0x96A006B0 / 0xAC1D7A81` | 0x89e1567c id=0x10000006, 1x 212x310 |
| Query panel ac3b72f6 | `0x00000000 / 0x96A006B0 / 0xAC3B72F6` | GZWinGen id=0x10000005, 1x 292x221 |
| Query panel ca566f94 | `0x00000000 / 0x96A006B0 / 0xCA566F94` | GZWinGen id=0x10000005, 1x 292x230 |
| Query panel ca8b8408 | `0x00000000 / 0x96A006B0 / 0xCA8B8408` | GZWinGen id=0x10000005, 1x 292x252 |
| Query panel ca8b8564 | `0x00000000 / 0x96A006B0 / 0xCA8B8564` | GZWinGen id=0x10000005, 1x 292x194 |
| Query panel ca8b96c2 | `0x00000000 / 0x96A006B0 / 0xCA8B96C2` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel ca8b9845 | `0x00000000 / 0x96A006B0 / 0xCA8B9845` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel ca8b9aa2 | `0x00000000 / 0x96A006B0 / 0xCA8B9AA2` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel ca8b9ce7 | `0x00000000 / 0x96A006B0 / 0xCA8B9CE7` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel ca8b9d40 | `0x00000000 / 0x96A006B0 / 0xCA8B9D40` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel cc097fc0 | `0x00000000 / 0x96A006B0 / 0xCC097FC0` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel cc1d71d3 | `0x00000000 / 0x96A006B0 / 0xCC1D71D3` | 0x89e1567c id=0x10000006, 1x 212x320 |
| Query panel cc1d72a2 | `0x00000000 / 0x96A006B0 / 0xCC1D72A2` | 0x89e1567c id=0x10000006, 1x 212x325 |
| Query panel cc1d778b | `0x00000000 / 0x96A006B0 / 0xCC1D778B` | 0x89e1567c id=0x10000006, 1x 212x320 |
| Query panel cc1d7a1f | `0x00000000 / 0x96A006B0 / 0xCC1D7A1F` | 0x89e1567c id=0x10000006, 1x 212x300 |
| Query panel cc1d824f | `0x00000000 / 0x96A006B0 / 0xCC1D824F` | 0x89e1567c id=0x10000006, 1x 212x300 |
| Query panel cc313f17 | `0x00000000 / 0x96A006B0 / 0xCC313F17` | GZWinGen id=0x10000005, 1x 292x193 |
| Query panel cc44f885 | `0x00000000 / 0x96A006B0 / 0xCC44F885` | 0x89e1567c id=0x10000006, 1x 212x320 |
| Query panel ea5655e4 | `0x00000000 / 0x96A006B0 / 0xEA5655E4` | GZWinGen id=0x10000005, 1x 292x283 |
| Query panel ea565970 | `0x00000000 / 0x96A006B0 / 0xEA565970` | GZWinGen id=0x10000005, 1x 292x275 |
| Query panel ea566a49 | `0x00000000 / 0x96A006B0 / 0xEA566A49` | GZWinGen id=0x10000005, 1x 292x172 |
| Query panel ea8b82db | `0x00000000 / 0x96A006B0 / 0xEA8B82DB` | GZWinGen id=0x10000005, 1x 292x255 |
| Query panel ec096e72 | `0x00000000 / 0x96A006B0 / 0xEC096E72` | GZWinGen id=0x10000005, 1x 292x134 |
| Query panel ec1a73ba | `0x00000000 / 0x96A006B0 / 0xEC1A73BA` | 0x89e1567c id=0x10000006, 1x 212x380 |
| Query panel ec1d74d5 | `0x00000000 / 0x96A006B0 / 0xEC1D74D5` | 0x89e1567c id=0x10000006, 1x 212x310 |
| Query panel ec1d7599 | `0x00000000 / 0x96A006B0 / 0xEC1D7599` | 0x89e1567c id=0x10000006, 1x 212x305 |
| Query panel ec1d75e2 | `0x00000000 / 0x96A006B0 / 0xEC1D75E2` | 0x89e1567c id=0x10000006, 1x 212x305 |
| Query panel ec1d77dd | `0x00000000 / 0x96A006B0 / 0xEC1D77DD` | 0x89e1567c id=0x10000006, 1x 212x330 |
| Query panel ec1d79d7 | `0x00000000 / 0x96A006B0 / 0xEC1D79D7` | 0x89e1567c id=0x10000006, 1x 212x360 |
| Query panel ec1d7a56 | `0x00000000 / 0x96A006B0 / 0xEC1D7A56` | 0x89e1567c id=0x10000006, 1x 212x300 |
| Query panel ec1d7efe | `0x00000000 / 0x96A006B0 / 0xEC1D7EFE` | 0x89e1567c id=0x10000006, 1x 212x300 |
| Query panel ec1d8125 | `0x00000000 / 0x96A006B0 / 0xEC1D8125` | 0x89e1567c id=0x10000006, 1x 212x320 |

## Target selection (2026-07-22 additions)

- QUIT DIALOG: both candidates inspected; BOTH are quit variants, both included.
  `I-4a551b4c` is the region-screen quit confirm (buttons "Quit SimCity 4" /
  "Cancel", 330x109); `I-8a5ab1cf` is the "Are you sure you want to quit
  SimCity 4?" Accept/Cancel variant (313x128, root at the (251,180) region-dialog
  anchor).
- START NEW CITY BUBBLE: `I-0a8cd184` (caption "Start New City", tail-anchored
  popup root 0x0a551c50). The game positions it (tail at the clicked tile), so
  only SIZES change -- safe to static-double.
- EXISTING-CITY BUBBLE: `I-ca539340` picked by content (city-name field, star
  rating, "Mayor Rating:", funds, population rows, gift/demolish/play buttons,
  same 0x0a551c50 popup root at (146,71)). EXCLUDED: `I-0b72f276` and
  `I-ea287193` -- 96-107 KB city-HUD region-view panels ("Map View"/"Data
  Views"/zone legend), not region-screen bubbles; also excluded per instruction:
  `2bc9060f`/`6bc9065a`/`898897de`/`ea2871aa` (city-HUD panels) and the
  G-4a87bfe8 hit (font table).
- PHOTO ALBUM: `I-4a8cc5ea` (captions "Photo Album"/"Albums"/"(add
  description here)"/"Close"; the snapshot viewfinder pane is inside this
  same script). EXCLUDED per instruction: `I-49889894` -- a 476x43 bottom
  strip, not a dialog.

## Package contents (266 entries, 2655005 bytes)

164 edited .UI scripts at their ORIGINAL TGIs (same-TGI overrides) + 101 PNGs:

| TGI | What |
|---|---|
| `0x00000000 / 0x96A006B0 / 0x6A9455C9` | edited Move In My Sim marker (green+red, #191) .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A7DF315` | edited Play Options .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA53F06E` | edited Audio Options .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A7E052F` | edited Graphic Options .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A5AB1CB` | edited Region Name (Create Region) .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A5AB1CE` | edited Delete Region confirm .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A5AB1CC` | edited Load Region .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A551B4C` | edited Quit confirm (region screen) .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A5AB1CF` | edited Quit confirm (are-you-sure) .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A8CD184` | edited Start New City bubble .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA539340` | edited Existing-city bubble .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A8CC5EA` | edited Photo Album .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A5AB1D0` | edited Delete City confirm .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A5AB1CD` | edited City Import .UI script |
| `0x00000000 / 0x96A006B0 / 0xEA8CC3C6` | edited Generic message box (code-driven confirms) .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA551016` | edited Credits .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A5A89D4` | edited Advisor toast (salmon) .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A5A89D5` | edited Advisor toast (salmon B) .UI script |
| `0x00000000 / 0x96A006B0 / 0x2BB16D50` | edited Advisor toast (green) .UI script |
| `0x00000000 / 0x96A006B0 / 0x0BBC06B6` | edited Advisor toast (blue) .UI script |
| `0x00000000 / 0x96A006B0 / 0x4BBC080F` | edited Advisor toast (peach) .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA56783A` | edited Building query (residential) .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A5672BF` | edited Building query (tall variant) .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A567DC1` | edited Building query (short variant) .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A41436C` | edited Obliterate City confirm .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A4D0C43` | edited Reconcile Edges (boundaries match) .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA4D0B22` | edited Reconcile Edges (highlighted areas confirm) .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A4D0A17` | edited Reconcile Edges (variant 3) .UI script |
| `0x00000000 / 0x96A006B0 / 0x6A553AA4` | edited Exit to Region confirm (in-city, 3-btn) .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A55161D` | edited Quit confirm (in-city, 3-btn) .UI script |
| `0x00000000 / 0x96A006B0 / 0xEAAEEC1B` | edited Exit to Region (in-city, play-city variant) .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A89B3F2` | edited Can't-save-during-disaster confirm .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A41436B` | edited Establish City .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A243D80` | edited Select A My Sim (Sim-mode sim picker) .UI script |
| `0x00000000 / 0x96A006B0 / 0x4BF325E8` | edited U-Drive-It Select vehicle for <MySim> .UI script |
| `0x00000000 / 0x96A006B0 / 0xABFAEF15` | edited U-Drive-It Select pedestrian style .UI script |
| `0x00000000 / 0x96A006B0 / 0xEA89B6C3` | edited Missing plugin-packs warning (city load) .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA8CBF0F` | edited Generic one-button notification popup .UI script |
| `0x00000000 / 0x96A006B0 / 0xEBD0D36C` | edited Select A Bridge (network across water) .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A2DD355` | edited Tutorial page (also an HTML-fed pane - see list D) .UI script |
| `0x00000000 / 0x96A006B0 / 0x6A5E73C0` | edited Tutorial exit confirm .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A5CF71D` | edited Game Over / Run for Senator .UI script |
| `0x00000000 / 0x96A006B0 / 0x8AA9AA14` | edited Startup splash 768x600 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAAAAF3D1` | edited Startup splash 800x600 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA5E60D1` | edited Clock time popup .UI script |
| `0x00000000 / 0x96A006B0 / 0x6B704690` | edited Label Tool (map annotation) .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA539343` | edited Region city-bubble stub (narrow) .UI script |
| `0x00000000 / 0x96A006B0 / 0xEBD0D36D` | edited Select A Bridge sibling button .UI script |
| `0x00000000 / 0x96A006B0 / 0xE9263D4C` | edited Text Entry prompt (Save City confirm) .UI script |
| `0x00000000 / 0x96A006B0 / 0xE9263DE5` | edited Set Lot Size .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A562A05` | edited Query panel 0a562a05 .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A8B819E` | edited Query panel 0a8b819e .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A8B98FE` | edited Query panel 0a8b98fe .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A8B9A67` | edited Query panel 0a8b9a67 .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A8B9C43` | edited Query panel 0a8b9c43 .UI script |
| `0x00000000 / 0x96A006B0 / 0x0A8B9C6A` | edited Query panel 0a8b9c6a .UI script |
| `0x00000000 / 0x96A006B0 / 0x0C1D56E4` | edited Query panel 0c1d56e4 .UI script |
| `0x00000000 / 0x96A006B0 / 0x0C1D730B` | edited Query panel 0c1d730b .UI script |
| `0x00000000 / 0x96A006B0 / 0x0C1D7737` | edited Query panel 0c1d7737 .UI script |
| `0x00000000 / 0x96A006B0 / 0x0C1D7974` | edited Query panel 0c1d7974 .UI script |
| `0x00000000 / 0x96A006B0 / 0x0C1D79AC` | edited Query panel 0c1d79ac .UI script |
| `0x00000000 / 0x96A006B0 / 0x0C1D7B60` | edited Query panel 0c1d7b60 .UI script |
| `0x00000000 / 0x96A006B0 / 0x0C1D7E71` | edited Query panel 0c1d7e71 .UI script |
| `0x00000000 / 0x96A006B0 / 0x0C1D81FC` | edited Query panel 0c1d81fc .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A554F6D` | edited Query panel 2a554f6d .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A5621EE` | edited Query panel 2a5621ee .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A564884` | edited Query panel 2a564884 .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A56675C` | edited Query panel 2a56675c .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A5E7490` | edited Query panel 2a5e7490 .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A8B7E1C` | edited Query panel 2a8b7e1c .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A8B97C1` | edited Query panel 2a8b97c1 .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A8B99D0` | edited Query panel 2a8b99d0 .UI script |
| `0x00000000 / 0x96A006B0 / 0x2A8B9DF2` | edited Query panel 2a8b9df2 .UI script |
| `0x00000000 / 0x96A006B0 / 0x2C02BA84` | edited Query panel 2c02ba84 .UI script |
| `0x00000000 / 0x96A006B0 / 0x2C096DE6` | edited Query panel 2c096de6 .UI script |
| `0x00000000 / 0x96A006B0 / 0x2C1D73CB` | edited Query panel 2c1d73cb .UI script |
| `0x00000000 / 0x96A006B0 / 0x2C1D784B` | edited Query panel 2c1d784b .UI script |
| `0x00000000 / 0x96A006B0 / 0x2C1D8024` | edited Query panel 2c1d8024 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A562DA5` | edited Query panel 4a562da5 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A565D13` | edited Query panel 4a565d13 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A5665EB` | edited Query panel 4a5665eb .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A566C14` | edited Query panel 4a566c14 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A566D6E` | edited Query panel 4a566d6e .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A5E7ED3` | edited Query panel 4a5e7ed3 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A8B7FE7` | edited Query panel 4a8b7fe7 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A8B9396` | edited Query panel 4a8b9396 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A8B9936` | edited Query panel 4a8b9936 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A8B9C92` | edited Query panel 4a8b9c92 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4A8B9DAB` | edited Query panel 4a8b9dab .UI script |
| `0x00000000 / 0x96A006B0 / 0x4C0969E2` | edited Query panel 4c0969e2 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4C1A68D2` | edited Query panel 4c1a68d2 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4C1D78F7` | edited Query panel 4c1d78f7 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4C1D7C0C` | edited Query panel 4c1d7c0c .UI script |
| `0x00000000 / 0x96A006B0 / 0x4C1D7C65` | edited Query panel 4c1d7c65 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4C1D7D40` | edited Query panel 4c1d7d40 .UI script |
| `0x00000000 / 0x96A006B0 / 0x4C47800E` | edited Query panel 4c47800e .UI script |
| `0x00000000 / 0x96A006B0 / 0x6A51506F` | edited Query panel 6a51506f .UI script |
| `0x00000000 / 0x96A006B0 / 0x6A555A84` | edited Query panel 6a555a84 .UI script |
| `0x00000000 / 0x96A006B0 / 0x6A561B3A` | edited Query panel 6a561b3a .UI script |
| `0x00000000 / 0x96A006B0 / 0x6A562F56` | edited Query panel 6a562f56 .UI script |
| `0x00000000 / 0x96A006B0 / 0x6A566151` | edited Query panel 6a566151 .UI script |
| `0x00000000 / 0x96A006B0 / 0x6A8B9875` | edited Query panel 6a8b9875 .UI script |
| `0x00000000 / 0x96A006B0 / 0x6A8B9ACC` | edited Query panel 6a8b9acc .UI script |
| `0x00000000 / 0x96A006B0 / 0x6A8B9AF3` | edited Query panel 6a8b9af3 .UI script |
| `0x00000000 / 0x96A006B0 / 0x6C1D789A` | edited Query panel 6c1d789a .UI script |
| `0x00000000 / 0x96A006B0 / 0x6C1D7AC3` | edited Query panel 6c1d7ac3 .UI script |
| `0x00000000 / 0x96A006B0 / 0x6C1D7F5C` | edited Query panel 6c1d7f5c .UI script |
| `0x00000000 / 0x96A006B0 / 0x6C1D8057` | edited Query panel 6c1d8057 .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A554483` | edited Query panel 8a554483 .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A5E7BD2` | edited Query panel 8a5e7bd2 .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A8B95B0` | edited Query panel 8a8b95b0 .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A8B9811` | edited Query panel 8a8b9811 .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A8B98A7` | edited Query panel 8a8b98a7 .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A8B9D12` | edited Query panel 8a8b9d12 .UI script |
| `0x00000000 / 0x96A006B0 / 0x8A948D49` | edited Query panel 8a948d49 .UI script |
| `0x00000000 / 0x96A006B0 / 0x8C1D7423` | edited Query panel 8c1d7423 .UI script |
| `0x00000000 / 0x96A006B0 / 0x8C1D76D5` | edited Query panel 8c1d76d5 .UI script |
| `0x00000000 / 0x96A006B0 / 0x8C3BD047` | edited Query panel 8c3bd047 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA554AEA` | edited Query panel aa554aea .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA555346` | edited Query panel aa555346 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA561F93` | edited Query panel aa561f93 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA565036` | edited Query panel aa565036 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA565F5B` | edited Query panel aa565f5b .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA5661EB` | edited Query panel aa5661eb .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA5BEF41` | edited Query panel aa5bef41 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA5E14CC` | edited Query panel aa5e14cc .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA8B9755` | edited Query panel aa8b9755 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA8B9971` | edited Query panel aa8b9971 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAA8B999E` | edited Query panel aa8b999e .UI script |
| `0x00000000 / 0x96A006B0 / 0xAC096AC7` | edited Query panel ac096ac7 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAC1D544D` | edited Query panel ac1d544d .UI script |
| `0x00000000 / 0x96A006B0 / 0xAC1D7548` | edited Query panel ac1d7548 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAC1D7A81` | edited Query panel ac1d7a81 .UI script |
| `0x00000000 / 0x96A006B0 / 0xAC3B72F6` | edited Query panel ac3b72f6 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA566F94` | edited Query panel ca566f94 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA8B8408` | edited Query panel ca8b8408 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA8B8564` | edited Query panel ca8b8564 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA8B96C2` | edited Query panel ca8b96c2 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA8B9845` | edited Query panel ca8b9845 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA8B9AA2` | edited Query panel ca8b9aa2 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA8B9CE7` | edited Query panel ca8b9ce7 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCA8B9D40` | edited Query panel ca8b9d40 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCC097FC0` | edited Query panel cc097fc0 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCC1D71D3` | edited Query panel cc1d71d3 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCC1D72A2` | edited Query panel cc1d72a2 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCC1D778B` | edited Query panel cc1d778b .UI script |
| `0x00000000 / 0x96A006B0 / 0xCC1D7A1F` | edited Query panel cc1d7a1f .UI script |
| `0x00000000 / 0x96A006B0 / 0xCC1D824F` | edited Query panel cc1d824f .UI script |
| `0x00000000 / 0x96A006B0 / 0xCC313F17` | edited Query panel cc313f17 .UI script |
| `0x00000000 / 0x96A006B0 / 0xCC44F885` | edited Query panel cc44f885 .UI script |
| `0x00000000 / 0x96A006B0 / 0xEA5655E4` | edited Query panel ea5655e4 .UI script |
| `0x00000000 / 0x96A006B0 / 0xEA565970` | edited Query panel ea565970 .UI script |
| `0x00000000 / 0x96A006B0 / 0xEA566A49` | edited Query panel ea566a49 .UI script |
| `0x00000000 / 0x96A006B0 / 0xEA8B82DB` | edited Query panel ea8b82db .UI script |
| `0x00000000 / 0x96A006B0 / 0xEC096E72` | edited Query panel ec096e72 .UI script |
| `0x00000000 / 0x96A006B0 / 0xEC1A73BA` | edited Query panel ec1a73ba .UI script |
| `0x00000000 / 0x96A006B0 / 0xEC1D74D5` | edited Query panel ec1d74d5 .UI script |
| `0x00000000 / 0x96A006B0 / 0xEC1D7599` | edited Query panel ec1d7599 .UI script |
| `0x00000000 / 0x96A006B0 / 0xEC1D75E2` | edited Query panel ec1d75e2 .UI script |
| `0x00000000 / 0x96A006B0 / 0xEC1D77DD` | edited Query panel ec1d77dd .UI script |
| `0x00000000 / 0x96A006B0 / 0xEC1D79D7` | edited Query panel ec1d79d7 .UI script |
| `0x00000000 / 0x96A006B0 / 0xEC1D7A56` | edited Query panel ec1d7a56 .UI script |
| `0x00000000 / 0x96A006B0 / 0xEC1D7EFE` | edited Query panel ec1d7efe .UI script |
| `0x00000000 / 0x96A006B0 / 0xEC1D8125` | edited Query panel ec1d8125 .UI script |
| `0x856DDBAC / 0x1ABE787D / 0x0C0E0F3C` | 2x IN-PLACE override of `{1abe787d,0c0e0f3c}` (128x75 px) |
| `0x856DDBAC / 0x1ABE787D / 0x144161E4` | 2x IN-PLACE override of `{1abe787d,144161e4}` (117x117 px) |
| `0x856DDBAC / 0x1ABE787D / 0x144161EE` | 2x IN-PLACE override of `{1abe787d,144161ee}` (270x270 px) |
| `0x856DDBAC / 0x1ABE787D / 0x14416220` | 2x IN-PLACE override of `{1abe787d,14416220}` (195x195 px) |
| `0x856DDBAC / 0x1ABE787D / 0x14416224` | 2x IN-PLACE override of `{1abe787d,14416224}` (195x195 px) |
| `0x856DDBAC / 0x1ABE787D / 0x14416240` | 2x IN-PLACE override of `{1abe787d,14416240}` (270x270 px) |
| `0x856DDBAC / 0x1ABE787D / 0x14416245` | 2x IN-PLACE override of `{1abe787d,14416245}` (192x24 px) |
| `0x856DDBAC / 0x1ABE787D / 0x14416246` | 2x IN-PLACE override of `{1abe787d,14416246}` (192x24 px) |
| `0x856DDBAC / 0x1ABE787D / 0x14416270` | 2x IN-PLACE override of `{1abe787d,14416270}` (845x579 px) |
| `0x856DDBAC / 0x1ABE787D / 0x14416271` | 2x IN-PLACE override of `{1abe787d,14416271}` (360x57 px) |
| `0x856DDBAC / 0x1ABE787D / 0x14416272` | 2x IN-PLACE override of `{1abe787d,14416272}` (120x36 px) |
| `0x856DDBAC / 0x1ABE787D / 0x14416273` | 2x IN-PLACE override of `{1abe787d,14416273}` (120x36 px) |
| `0x856DDBAC / 0x1ABE787D / 0x8C0E0F2D` | 2x IN-PLACE override of `{1abe787d,8c0e0f2d}` (618x557 px) |
| `0x856DDBAC / 0x1ABE787D / 0xB971F101` | 2x CLONE of `{1abe787d,ea32f100}` (54x62 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13E14FB7` | 2x IN-PLACE override of `{46a006b0,13e14fb7}` (788x426 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F15213` | 2x IN-PLACE override of `{46a006b0,13f15213}` (69x146 px) |
| `0x856DDBAC / 0x46A006B0 / 0x40B25215` | 2x CLONE of `{46a006b0,13f15214}` (69x146 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F15250` | 2x IN-PLACE override of `{46a006b0,13f15250}` (651x572 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F15251` | 2x IN-PLACE override of `{46a006b0,13f15251}` (212x33 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F15253` | 2x IN-PLACE override of `{46a006b0,13f15253}` (212x45 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F15254` | 2x IN-PLACE override of `{46a006b0,13f15254}` (212x77 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F15255` | 2x IN-PLACE override of `{46a006b0,13f15255}` (272x57 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F15257` | 2x IN-PLACE override of `{46a006b0,13f15257}` (212x53 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F15258` | 2x IN-PLACE override of `{46a006b0,13f15258}` (60x20 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F15259` | 2x IN-PLACE override of `{46a006b0,13f15259}` (60x20 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F1525E` | 2x IN-PLACE override of `{46a006b0,13f1525e}` (300x74 px) |
| `0x856DDBAC / 0x46A006B0 / 0x13F1525F` | 2x IN-PLACE override of `{46a006b0,13f1525f}` (180x45 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14015586` | 2x IN-PLACE override of `{46a006b0,14015586}` (128x33 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161E0` | 2x IN-PLACE override of `{46a006b0,144161e0}` (132x30 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161E2` | 2x IN-PLACE override of `{46a006b0,144161e2}` (132x32 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161E4` | 2x IN-PLACE override of `{46a006b0,144161e4}` (117x117 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161E7` | 2x IN-PLACE override of `{46a006b0,144161e7}` (80x18 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161EB` | 2x IN-PLACE override of `{46a006b0,144161eb}` (180x45 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161EE` | 2x IN-PLACE override of `{46a006b0,144161ee}` (270x270 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161F1` | 2x IN-PLACE override of `{46a006b0,144161f1}` (540x216 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161F2` | 2x IN-PLACE override of `{46a006b0,144161f2}` (540x216 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161F3` | 2x IN-PLACE override of `{46a006b0,144161f3}` (131x141 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161F4` | 2x IN-PLACE override of `{46a006b0,144161f4}` (131x141 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161F5` | 2x IN-PLACE override of `{46a006b0,144161f5}` (240x45 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161F6` | 2x IN-PLACE override of `{46a006b0,144161f6}` (240x45 px) |
| `0x856DDBAC / 0x46A006B0 / 0x144161F9` | 2x IN-PLACE override of `{46a006b0,144161f9}` (132x32 px) |
| `0x856DDBAC / 0x46A006B0 / 0x1441620E` | 2x IN-PLACE override of `{46a006b0,1441620e}` (18x48 px) |
| `0x856DDBAC / 0x46A006B0 / 0x1441620F` | 2x IN-PLACE override of `{46a006b0,1441620f}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416210` | 2x IN-PLACE override of `{46a006b0,14416210}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416211` | 2x IN-PLACE override of `{46a006b0,14416211}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416212` | 2x IN-PLACE override of `{46a006b0,14416212}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416214` | 2x IN-PLACE override of `{46a006b0,14416214}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416215` | 2x IN-PLACE override of `{46a006b0,14416215}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416216` | 2x IN-PLACE override of `{46a006b0,14416216}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416217` | 2x IN-PLACE override of `{46a006b0,14416217}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416218` | 2x IN-PLACE override of `{46a006b0,14416218}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416219` | 2x IN-PLACE override of `{46a006b0,14416219}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x1441621A` | 2x IN-PLACE override of `{46a006b0,1441621a}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x1441621B` | 2x IN-PLACE override of `{46a006b0,1441621b}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x1441621C` | 2x IN-PLACE override of `{46a006b0,1441621c}` (36x66 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416220` | 2x IN-PLACE override of `{46a006b0,14416220}` (195x195 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416221` | 2x IN-PLACE override of `{46a006b0,14416221}` (195x195 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416222` | 2x IN-PLACE override of `{46a006b0,14416222}` (195x195 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416223` | 2x IN-PLACE override of `{46a006b0,14416223}` (195x195 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416225` | 2x IN-PLACE override of `{46a006b0,14416225}` (195x195 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416226` | 2x IN-PLACE override of `{46a006b0,14416226}` (195x195 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416227` | 2x IN-PLACE override of `{46a006b0,14416227}` (195x195 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416228` | 2x IN-PLACE override of `{46a006b0,14416228}` (195x195 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416229` | 2x IN-PLACE override of `{46a006b0,14416229}` (195x195 px) |
| `0x856DDBAC / 0x46A006B0 / 0x1441622A` | 2x IN-PLACE override of `{46a006b0,1441622a}` (195x195 px) |
| `0x856DDBAC / 0x46A006B0 / 0x1441622C` | 2x IN-PLACE override of `{46a006b0,1441622c}` (63x72 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416231` | 2x IN-PLACE override of `{46a006b0,14416231}` (63x98 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416240` | 2x IN-PLACE override of `{46a006b0,14416240}` (270x270 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416243` | 2x IN-PLACE override of `{46a006b0,14416243}` (66x56 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416245` | 2x IN-PLACE override of `{46a006b0,14416245}` (192x24 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416264` | 2x IN-PLACE override of `{46a006b0,14416264}` (24x24 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416280` | 2x IN-PLACE override of `{46a006b0,14416280}` (710x462 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416321` | 2x IN-PLACE override of `{46a006b0,14416321}` (324x233 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416322` | 2x IN-PLACE override of `{46a006b0,14416322}` (387x359 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416323` | 2x IN-PLACE override of `{46a006b0,14416323}` (80x20 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416324` | 2x IN-PLACE override of `{46a006b0,14416324}` (216x44 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416325` | 2x IN-PLACE override of `{46a006b0,14416325}` (132x48 px) |
| `0x856DDBAC / 0x46A006B0 / 0x14416326` | 2x IN-PLACE override of `{46a006b0,14416326}` (332x69 px) |
| `0x856DDBAC / 0x46A006B0 / 0x2BC3AC85` | 2x IN-PLACE override of `{46a006b0,2bc3ac85}` (131x141 px) |
| `0x856DDBAC / 0x46A006B0 / 0x2C201CB0` | 2x IN-PLACE override of `{46a006b0,2c201cb0}` (660x54 px) |
| `0x856DDBAC / 0x46A006B0 / 0x2C201CB1` | 2x IN-PLACE override of `{46a006b0,2c201cb1}` (660x54 px) |
| `0x856DDBAC / 0x46A006B0 / 0x2C201CB2` | 2x IN-PLACE override of `{46a006b0,2c201cb2}` (660x54 px) |
| `0x856DDBAC / 0x46A006B0 / 0x46A006A4` | 2x IN-PLACE override of `{46a006b0,46a006a4}` (108x108 px) |
| `0x856DDBAC / 0x46A006B0 / 0x46A006A6` | 2x IN-PLACE override of `{46a006b0,46a006a6}` (288x24 px) |
| `0x856DDBAC / 0x46A006B0 / 0x46A006A7` | 2x IN-PLACE override of `{46a006b0,46a006a7}` (108x27 px) |
| `0x856DDBAC / 0x46A006B0 / 0x4BC3A5AE` | 2x IN-PLACE override of `{46a006b0,4bc3a5ae}` (240x45 px) |
| `0x856DDBAC / 0x46A006B0 / 0x4BFC52C2` | 2x IN-PLACE override of `{46a006b0,4bfc52c2}` (324x74 px) |
| `0x856DDBAC / 0x46A006B0 / 0x4C02B518` | 2x IN-PLACE override of `{46a006b0,4c02b518}` (236x174 px) |
| `0x856DDBAC / 0x46A006B0 / 0x4C0F0D31` | 2x IN-PLACE override of `{46a006b0,4c0f0d31}` (290x69 px) |
| `0x856DDBAC / 0x46A006B0 / 0x6BB93CB5` | 2x IN-PLACE override of `{46a006b0,6bb93cb5}` (296x372 px) |
| `0x856DDBAC / 0x46A006B0 / 0x8BC38238` | 2x IN-PLACE override of `{46a006b0,8bc38238}` (540x216 px) |
| `0x856DDBAC / 0x46A006B0 / 0xCBBAB0AE` | 2x IN-PLACE override of `{46a006b0,cbbab0ae}` (576x542 px) |
| `0x856DDBAC / 0x46A006B0 / 0xCBEC3DB2` | 2x IN-PLACE override of `{46a006b0,cbec3db2}` (540x375 px) |
| `0x856DDBAC / 0x46A006B0 / 0xCBFB3730` | 2x IN-PLACE override of `{46a006b0,cbfb3730}` (17x17 px) |
| `0x856DDBAC / 0x46A006B0 / 0xCBFB3731` | 2x IN-PLACE override of `{46a006b0,cbfb3731}` (33x17 px) |
| `0x856DDBAC / 0x46A006B0 / 0xCBFB3732` | 2x IN-PLACE override of `{46a006b0,cbfb3732}` (50x17 px) |
| `0x856DDBAC / 0x46A006B0 / 0xCC1980EB` | 2x IN-PLACE override of `{46a006b0,cc1980eb}` (21x44 px) |
| `0x856DDBAC / 0x46A006B0 / 0xCC1980EC` | 2x IN-PLACE override of `{46a006b0,cc1980ec}` (21x44 px) |
| `0x856DDBAC / 0x46A006B0 / 0xCC1A735D` | 2x IN-PLACE override of `{46a006b0,cc1a735d}` (132x32 px) |
| `0x856DDBAC / 0x46A006B0 / 0xB1F56DBA` | 2x CLONE of `{46a006b0,e2b66db8}` (180x45 px) |
| `0x856DDBAC / 0x46A006B0 / 0xEA7F0EAF` | 2x IN-PLACE override of `{46a006b0,ea7f0eaf}` (1200x900 px) |

## Global art plan (117 distinct TGIs; ONE decision per TGI across all 164 targets)

| image={gid,iid} | Used by | Decision | Detail |
|---|---|---|---|
| `{00237ee7,0ea08a4a}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{1abe787d,0c0e0f3c}` | ebd0d36c | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,144161e4}` | 0a7df315, 8a7e052f, 8a5ab1cb, 8a5ab1cc, 4a8cc5ea, 8a5ab1cd, ea8cc3c6, ea89b6c3, ca8cbf0f, 6b704690 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,144161ee}` | 0a7df315, 8a7e052f, 8a5ab1cb, 8a5ab1cc, 8a5ab1cf, 4a8cc5ea, 8a5ab1cd, ea8cc3c6, 0a4d0c43, ca4d0b22, ea89b6c3, ca8cbf0f, 6b704690 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,14416220}` | aa561f93 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,14416224}` | 0a562a05 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,14416240}` | 0a7df315, 8a7e052f, 8a5ab1ce, 8a5ab1cf, 8a5ab1d0, 4a89b3f2, 0a243d80 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,14416245}` | 0a7df315 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,14416246}` | 8a7e052f, 8a5ab1cb, 2a41436b | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,14416270}` | 4a8cc5ea | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,14416271}` | 4a8cc5ea | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,14416272}` | 4a8cc5ea | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,14416273}` | 4a8cc5ea | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,8c0e0f2d}` | ebd0d36c | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{1abe787d,ea32f100}` | 6a9455c9 | CLONED -> `{1abe787d,b971f101}` | shared with 2 other .UI file(s) not 2x-handled |
| `{3e53026e,274ddedd}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{40ddc72b,e740ca77}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{46a006b0,13e14fb7}` | ca551016 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f15213}` | 6a9455c9 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f15214}` | 6a9455c9 | CLONED -> `{46a006b0,40b25215}` | shared with 2 other .UI file(s) not 2x-handled |
| `{46a006b0,13f15250}` | 0a243d80 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f15251}` | 0a243d80 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f15253}` | 0a243d80 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f15254}` | 0a243d80 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f15255}` | 0a243d80 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f15257}` | 0a243d80 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f15258}` | 0a243d80, 4bf325e8, abfaef15 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f15259}` | 0a243d80, 4bf325e8, abfaef15 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f1525e}` | 0a243d80 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,13f1525f}` | 0a243d80, 4bf325e8, abfaef15 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14015586}` | ca539340, 4a8cc5ea | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161e0}` | 0c1d56e4, 0c1d730b, 0c1d7737, 0c1d7974, 0c1d79ac, 0c1d7b60, 0c1d7e71, 0c1d81fc, 2c02ba84, 2c1d73cb, 2c1d784b, 2c1d8024, 4c1a68d2, 4c1d78f7, 4c1d7c0c, 4c1d7c65, 4c1d7d40, 6c1d789a, 6c1d7ac3, 6c1d7f5c, 6c1d8057, 8c1d7423, 8c1d76d5, 8c3bd047, ac1d544d, ac1d7548, ac1d7a81, cc1d71d3, cc1d72a2, cc1d778b, cc1d7a1f, cc1d824f, cc44f885, ec1a73ba, ec1d74d5, ec1d7599, ec1d75e2, ec1d77dd, ec1d79d7, ec1d7a56, ec1d7efe, ec1d8125 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161e2}` | 0c1d56e4, 0c1d730b, 0c1d7737, 0c1d7974, 0c1d79ac, 0c1d7b60, 0c1d7e71, 0c1d81fc, 2c02ba84, 2c1d73cb, 2c1d784b, 2c1d8024, 4c1a68d2, 4c1d78f7, 4c1d7c0c, 4c1d7c65, 4c1d7d40, 6c1d789a, 6c1d7ac3, 6c1d7f5c, 6c1d8057, 8c1d7423, 8c1d76d5, 8c3bd047, ac1d544d, ac1d7548, ac1d7a81, cc1d71d3, cc1d72a2, cc1d778b, cc1d7a1f, cc1d824f, cc44f885, ec1a73ba, ec1d74d5, ec1d7599, ec1d75e2, ec1d77dd, ec1d79d7, ec1d7a56, ec1d7efe, ec1d8125 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161e4}` | ca53f06e, 4a551b4c, 6a553aa4, 0a55161d, eaaeec1b, 2a41436b, 0a5cf71d, 0c1d56e4, 0c1d730b, 0c1d7737, 0c1d7974, 0c1d79ac, 0c1d7b60, 0c1d7e71, 0c1d81fc, 2c1d73cb, 2c1d784b, 2c1d8024, 4c1a68d2, 4c1d78f7, 4c1d7c0c, 4c1d7c65, 4c1d7d40, 6c1d789a, 6c1d7ac3, 6c1d7f5c, 6c1d8057, 8c1d7423, 8c1d76d5, 8c3bd047, ac1d544d, ac1d7548, ac1d7a81, cc1d71d3, cc1d72a2, cc1d778b, cc1d7a1f, cc1d824f, cc44f885, ec1a73ba, ec1d74d5, ec1d7599, ec1d75e2, ec1d77dd, ec1d79d7, ec1d7a56, ec1d7efe, ec1d8125 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161e7}` | aa5e60d1 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161eb}` | 0a7df315, ca53f06e, 8a7e052f, 8a5ab1cb, 8a5ab1ce, 8a5ab1cc, 4a551b4c, 8a5ab1cf, 4a8cc5ea, 8a5ab1d0, 8a5ab1cd, ea8cc3c6, ca551016, ca56783a, 4a5672bf, 2a567dc1, 0a4d0c43, ca4d0b22, 8a4d0a17, 6a553aa4, 0a55161d, eaaeec1b, 4a89b3f2, 0a243d80, ea89b6c3, ca8cbf0f, ebd0d36c, 0a2dd355, 6a5e73c0, 6b704690, 0a562a05, 0a8b819e, 0a8b98fe, 0a8b9a67, 0a8b9c43, 0a8b9c6a, 2a554f6d, 2a5621ee, 2a564884, 2a56675c, 2a5e7490, 2a8b7e1c, 2a8b97c1, 2a8b99d0, 2a8b9df2, 2c096de6, 4a562da5, 4a565d13, 4a5665eb, 4a566c14, 4a566d6e, 4a5e7ed3, 4a8b7fe7, 4a8b9396, 4a8b9936, 4a8b9c92, 4a8b9dab, 4c0969e2, 4c47800e, 6a51506f, 6a555a84, 6a561b3a, 6a562f56, 6a566151, 6a8b9875, 6a8b9acc, 6a8b9af3, 8a554483, 8a5e7bd2, 8a8b95b0, 8a8b9811, 8a8b98a7, 8a8b9d12, 8a948d49, aa554aea, aa555346, aa561f93, aa565036, aa565f5b, aa5661eb, aa5bef41, aa5e14cc, aa8b9755, aa8b9971, aa8b999e, ac096ac7, ac3b72f6, ca566f94, ca8b8408, ca8b8564, ca8b96c2, ca8b9845, ca8b9aa2, ca8b9ce7, ca8b9d40, cc097fc0, cc313f17, ea5655e4, ea565970, ea566a49, ea8b82db, ec096e72 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161ee}` | 0a7df315, ca53f06e, 8a7e052f, 8a5ab1cb, 8a5ab1cc, 8a5ab1cd, 2a41436c, 2a41436b, ea89b6c3, 0a5cf71d | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161f1}` | 4a5a89d4, 4bbc080f | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161f2}` | 4a5a89d5, 0bbc06b6 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161f3}` | 4a5a89d4, 4bbc080f | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161f4}` | 4a5a89d5, 0bbc06b6 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161f5}` | 4a5a89d4, 4bbc080f | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161f6}` | 4a5a89d5, 0bbc06b6 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,144161f9}` | 4bf325e8, abfaef15, 0c1d56e4, 0c1d730b, 0c1d7737, 0c1d7974, 0c1d79ac, 0c1d7b60, 0c1d7e71, 0c1d81fc, 2c02ba84, 2c1d73cb, 2c1d784b, 2c1d8024, 4c1a68d2, 4c1d78f7, 4c1d7c0c, 4c1d7c65, 4c1d7d40, 6c1d789a, 6c1d7ac3, 6c1d7f5c, 6c1d8057, 8c1d7423, 8c1d76d5, 8c3bd047, ac1d544d, ac1d7548, ac1d7a81, cc1d71d3, cc1d72a2, cc1d778b, cc1d7a1f, cc1d824f, cc44f885, ec1a73ba, ec1d74d5, ec1d7599, ec1d75e2, ec1d77dd, ec1d79d7, ec1d7a56, ec1d7efe, ec1d8125 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,1441620e}` | ca56783a, 4a5672bf, 2a567dc1 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,1441620f}` | 4c47800e | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416210}` | 2a564884, 2a8b7e1c, 4a8b7fe7, 6a555a84, 8a554483, aa565036, ca8b8564, ea8b82db | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416211}` | 6a51506f | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416212}` | 0a8b819e, 2a554f6d, aa555346 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416214}` | 6a561b3a | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416215}` | 4a562da5, cc313f17 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416216}` | aa554aea, ca8b8408 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416217}` | 2a5621ee, aa561f93, aa5bef41 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416218}` | 6a562f56, ea5655e4 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416219}` | 8a948d49, ea565970 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,1441621a}` | 6a566151, ac3b72f6 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,1441621b}` | 4a565d13 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,1441621c}` | aa5661eb | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416220}` | 2a5e7490, 4a566c14, 4a566d6e, 4a5e7ed3, 8a5e7bd2, aa5e14cc, ca566f94, ea566a49 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416221}` | 2a564884, 2a56675c, 6a555a84, 8a554483, aa554aea, aa565036 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416222}` | ca56783a | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416223}` | 6a51506f | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416225}` | 0a8b819e, 0a8b98fe, 0a8b9a67, 0a8b9c43, 0a8b9c6a, 2a8b7e1c, 2a8b97c1, 2a8b99d0, 2a8b9df2, 2c096de6, 4a8b7fe7, 4a8b9396, 4a8b9936, 4a8b9c92, 4a8b9dab, 4c0969e2, 6a8b9875, 6a8b9acc, 6a8b9af3, 8a8b95b0, 8a8b9811, 8a8b98a7, 8a8b9d12, aa8b9755, aa8b9971, aa8b999e, ac096ac7, ca8b8408, ca8b8564, ca8b96c2, ca8b9845, ca8b9aa2, ca8b9ce7, ca8b9d40, cc097fc0, ea8b82db, ec096e72 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416226}` | 2a567dc1 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416227}` | 2a554f6d, aa555346 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416228}` | 4a5672bf | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416229}` | 4a562da5, 4a565d13, 4a5665eb, 4c47800e, 6a561b3a, 6a566151, aa565f5b, aa5661eb, ac3b72f6, cc313f17 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,1441622a}` | 2a5621ee, 6a562f56, 8a948d49, aa5bef41, ea5655e4, ea565970 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,1441622c}` | 4a5672bf | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416231}` | ca539343 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416240}` | 0a4d0c43, ca4d0b22, 8a4d0a17, 4a89b3f2, 6a5e73c0 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416243}` | 2a41436b | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416245}` | ca53f06e, 8a7e052f, ca56783a, 4a5672bf, 2a567dc1, 8a4d0a17 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416264}` | ca53f06e | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416280}` | 0a2dd355 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416321}` | 0a8cd184 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416322}` | ca539340 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416323}` | ca539340 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416324}` | 0a8cd184, ca539340 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416325}` | 0a8cd184, ca539340 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,14416326}` | 0a8cd184, ca539340 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,2bc3ac85}` | 2bb16d50 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,2c201cb0}` | 4bf325e8 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,2c201cb1}` | 4bf325e8 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,2c201cb2}` | 4bf325e8 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,46a006a4}` | aa5e60d1 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,46a006a6}` | ebd0d36c | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,46a006a7}` | ca53f06e, ebd0d36c, 2a554f6d, 2a564884, 2a8b7e1c, 4a8b7fe7, 6a51506f, 6a555a84, 6a562f56, 8a554483, aa554aea, aa565036, ca8b8408, ea5655e4, ea8b82db | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,4bc3a5ae}` | 2bb16d50 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,4bfc52c2}` | 4bf325e8, abfaef15 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,4c02b518}` | 2c02ba84 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,4c0f0d31}` | 2c02ba84 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,6b998f30}` | 4bf325e8, abfaef15 | LEFT 1x | no 2x asset in upscale preview set |
| `{46a006b0,6bb93cb5}` |  | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,8bc38238}` | 2bb16d50 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,b5cfffff}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{46a006b0,cbbab0ae}` | 4bf325e8, abfaef15 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,cbec3db2}` | 4bf325e8, abfaef15 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,cbfb3730}` | ca539340 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,cbfb3731}` | ca539340 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,cbfb3732}` | ca539340 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,cc1980eb}` | 0c1d56e4, 4c1d7c65, ec1a73ba | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,cc1980ec}` | 0c1d730b, 0c1d7974, 0c1d81fc, 4c1d78f7, 4c1d7c65, 6c1d7f5c, ac1d7a81, ec1a73ba, ec1d75e2, ec1d77dd | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,cc1a735d}` | 0c1d56e4, 0c1d730b, 0c1d7737, 0c1d7974, 0c1d79ac, 0c1d7b60, 0c1d7e71, 0c1d81fc, 2c1d73cb, 2c1d784b, 2c1d8024, 4c1a68d2, 4c1d78f7, 4c1d7c0c, 4c1d7c65, 4c1d7d40, 6c1d789a, 6c1d7ac3, 6c1d7f5c, 6c1d8057, 8c1d7423, 8c1d76d5, 8c3bd047, ac1d544d, ac1d7548, ac1d7a81, cc1d71d3, cc1d72a2, cc1d778b, cc1d7a1f, cc1d824f, cc44f885, ec1a73ba, ec1d74d5, ec1d7599, ec1d75e2, ec1d77dd, ec1d79d7, ec1d7a56, ec1d7efe, ec1d8125 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{46a006b0,d685c764}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{46a006b0,e2b66db8}` | 4a8cc5ea, 2a41436c, 2a41436b, 0a243d80, 4bf325e8, abfaef15, 0a5cf71d, e9263d4c, e9263de5 | CLONED -> `{46a006b0,b1f56dba}` | shared with 15 other .UI file(s) not 2x-handled [0xB1F56DB9 collision: selective-safe planned clone; XOR 0x53430001 collided, fell back to 0x53430002] |
| `{46a006b0,ea32f104}` | 0a243d80, 4bf325e8, abfaef15 | LEFT 1x | no 2x asset in upscale preview set |
| `{46a006b0,ea7f0eae}` | 8aa9aa14 | LEFT 1x | no 2x asset in upscale preview set |
| `{46a006b0,ea7f0eaf}` | aaaaf3d1 | 2x IN PLACE | exclusive to the 164 target scripts (no other unhandled referrer) |
| `{968b9ea5,df7a1654}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{bd85e83a,a6122c8d}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{be484ac7,7aeb8e7d}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{bf73248c,f0b38b15}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{c3e123bd,cfe4e42f}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{c53f65d9,71651db9}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{ca120e98,2d7c4d1b}` |  | LEFT 1x | no 2x asset in upscale preview set |
| `{d4ff97fa,c3406512}` |  | LEFT 1x | no 2x asset in upscale preview set |

Clone IID scheme: `iid ^ 0x53430001` (selective-safe convention), each verified
collision-free against the full game PNG store (`extracted-png-tgi.csv`, 2280 TGIs),
every .UI-referenced TGI (431), selective-safe's 12 planned clone TGIs, and the
other clones of this run. Fallback `^ 0x53430002` was needed for 1 TGI(s)
whose primary slot is already claimed by a selective-safe planned clone: `{46a006b0,e2b66db8}`.

## Per-dialog edits

Common to all: EVERY `area=(x1,y1,x2,y2)` doubled (corner-format absolute px;
the first `id=` in a file is not always the meaningful root, so ALL areas are
doubled regardless); `imagerect=` doubled ONLY where that control's art went 2x;
`font=NAME` converted to GUID form via `tools\fonts\FontStyle.candidate.ini`
(proven deserializer path, type-6 token -> SetFontStyleByGUID; fonts are already
confirmed loading in-game, so this is belt-and-braces consistency, not the size
fix). Every edited script was re-parsed and machine-verified node-for-node
(areas exactly 2x, refs retargeted per plan, imagerects 2x iff art 2x, fonts in
GUID form) before packing.

### Move In My Sim marker (green+red, #191) (`I-6a9455c9`, source `T-00000000_G-96a006b0_I-6a9455c9.ui`)

- Root 0x89e1567c id=0x27df05bf: area `(109,151,155,248)` -> `(164,227,233,372)` (46x97 -> 69x145).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{1abe787d,ea32f100}` x2 -> clone; `{46a006b0,13f15213}` x1 2x in place; `{46a006b0,13f15214}` x3 -> clone.
- `imagerect=` doubled (4):
  - GZWinBMP `(0,0,36,41)` -> `(0,0,54,62)`
  - GZWinBMP `(0,0,46,97)` -> `(0,0,69,146)`
  - GZWinBMP `(0,0,36,41)` -> `(0,0,54,62)`
  - GZWinBMP `(0,0,46,97)` -> `(0,0,69,146)`
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: none (no name-form font tokens).

### Play Options (`I-0a7df315`, source `T-00000000_G-96a006b0_I-0a7df315.ui`)

- Root GZWinGen id=0x2a57db82: area `(0,0,699,523)` -> `(0,0,1049,785)` (699x523 -> 1049x785).
  NOTE: this root gen is larger than the visible dialog art -- expected,
  doubled as-is by design.
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{1abe787d,144161e4}` x1 2x in place; `{1abe787d,144161ee}` x1 2x in place; `{1abe787d,14416240}` x2 2x in place; `{1abe787d,14416245}` x5 2x in place; `{46a006b0,144161eb}` x6 2x in place; `{46a006b0,144161ee}` x1 2x in place.
- `imagerect=` doubled (3):
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
  - GZWinBMP `(20,35,180,180)` -> `(30,53,270,270)`
  - GZWinBMP `(12,32,180,180)` -> `(18,48,270,270)`
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x7 -> `0x4a809917` (26 px ini, was 13); `GenButton` x6 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Audio Options (`I-ca53f06e`, source `T-00000000_G-96a006b0_I-ca53f06e.ui`)

- Root GZWinGen id=0xea53f5db: area `(44,20,374,491)` -> `(66,30,561,737)` (330x471 -> 495x707).
- `area=` rects doubled: 24 (every one in the script; 24 controls total).
- Art refs: `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161eb}` x4 2x in place; `{46a006b0,144161ee}` x3 2x in place; `{46a006b0,14416245}` x3 2x in place; `{46a006b0,14416264}` x2 2x in place; `{46a006b0,46a006a7}` x2 2x in place.
- `imagerect=` doubled (6):
  - GZWinBMP `(0,0,16,16)` -> `(0,0,24,24)`
  - GZWinBMP `(5,18,180,180)` -> `(8,27,270,270)`
  - GZWinBMP `(0,0,16,16)` -> `(0,0,24,24)`
  - GZWinBMP `(5,18,180,180)` -> `(8,27,270,270)`
  - GZWinBMP `(5,18,180,180)` -> `(8,27,270,270)`
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
- 10 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyLight` x1 -> `0x4a809918` (26 px ini, was 13); `GenBodyMedium` x6 -> `0x4a809917` (26 px ini, was 13); `GenButton` x4 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `GenSubHeader` x1 -> `0x4a80991a` (32 px ini, was 16).

### Graphic Options (`I-8a7e052f`, source `T-00000000_G-96a006b0_I-8a7e052f.ui`)

- Root GZWinGen id=0x2a57cb82: area `(3,0,725,558)` -> `(5,0,1088,837)` (722x558 -> 1083x837).
  NOTE: this root gen is larger than the visible dialog art -- expected,
  doubled as-is by design.
- `area=` rects doubled: 81 (every one in the script; 81 controls total).
- Art refs: `{1abe787d,144161e4}` x1 2x in place; `{1abe787d,144161ee}` x1 2x in place; `{1abe787d,14416240}` x2 2x in place; `{1abe787d,14416246}` x26 2x in place; `{46a006b0,144161eb}` x4 2x in place; `{46a006b0,144161ee}` x1 2x in place; `{46a006b0,14416245}` x5 2x in place.
- `imagerect=` doubled (3):
  - GZWinBMP `(12,32,180,180)` -> `(18,48,270,270)`
  - GZWinBMP `(22,35,180,180)` -> `(33,53,270,270)`
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
- 37 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x32 -> `0x4a809917` (26 px ini, was 13); `GenButton` x4 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Region Name (Create Region) (`I-8a5ab1cb`, source `T-00000000_G-96a006b0_I-8a5ab1cb.ui`)

- Root GZWinGen id=0xea5ba0d1: area `(251,180,581,348)` -> `(377,270,872,522)` (330x168 -> 495x252).
- `area=` rects doubled: 12 (every one in the script; 12 controls total).
- Art refs: `{1abe787d,144161e4}` x1 2x in place; `{1abe787d,144161ee}` x1 2x in place; `{1abe787d,14416246}` x2 2x in place; `{46a006b0,144161eb}` x2 2x in place; `{46a006b0,144161ee}` x1 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(12,37,180,180)` -> `(18,56,270,270)`
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
- 5 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyLight` x1 -> `0x4a809918` (26 px ini, was 13); `GenBodyMedium` x3 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Delete Region confirm (`I-8a5ab1ce`, source `T-00000000_G-96a006b0_I-8a5ab1ce.ui`)

- Root GZWinGen id=0x6a5ba20c: area `(251,180,551,338)` -> `(377,270,827,507)` (300x158 -> 450x237).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{1abe787d,14416240}` x2 2x in place; `{46a006b0,144161eb}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(12,24,180,180)` -> `(18,36,270,270)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16).

### Load Region (`I-8a5ab1cc`, source `T-00000000_G-96a006b0_I-8a5ab1cc.ui`)

- Root GZWinGen id=0x4a5ba0e7: area `(171,103,501,291)` -> `(257,155,752,437)` (330x188 -> 495x282).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{1abe787d,144161e4}` x1 2x in place; `{1abe787d,144161ee}` x1 2x in place; `{46a006b0,144161eb}` x2 2x in place; `{46a006b0,144161ee}` x1 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
  - GZWinBMP `(12,35,180,180)` -> `(18,53,270,270)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Quit confirm (region screen) (`I-4a551b4c`, source `T-00000000_G-96a006b0_I-4a551b4c.ui`)

- Root GZWinGen id=0xaa921f4f: area `(332,170,662,279)` -> `(498,255,993,419)` (330x109 -> 495x164).
- `area=` rects doubled: 4 (every one in the script; 4 controls total).
- Art refs: `{46a006b0,144161e4}` x1 2x in place; `{46a006b0,144161eb}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenButton` x2 -> `0x4a809919` (32 px ini, was 16).

### Quit confirm (are-you-sure) (`I-8a5ab1cf`, source `T-00000000_G-96a006b0_I-8a5ab1cf.ui`)

- Root GZWinGen id=(no id): area `(251,180,564,308)` -> `(377,270,846,462)` (313x128 -> 469x192).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{1abe787d,144161ee}` x1 2x in place; `{1abe787d,14416240}` x1 2x in place; `{46a006b0,144161eb}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(12,37,180,180)` -> `(18,56,270,270)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16).

### Start New City bubble (`I-0a8cd184`, source `T-00000000_G-96a006b0_I-0a8cd184.ui`)

- Root 0x89e1567c id=0x0a551c50: area `(146,71,362,236)` -> `(219,107,543,354)` (216x165 -> 324x247).
  NOTE: tail-anchored popup -- the GAME positions it (tail at the clicked
  tile), so the doubled origin is irrelevant; only the doubled SIZE is the
  assertion. Its body+tail bubble art `{46a006b0,14416321}` IS among the doubled TGIs (see
  the art plan), split across two BMPs whose `imagerect` slices were
  doubled with it.
- `area=` rects doubled: 9 (every one in the script; 9 controls total).
- Art refs: `{46a006b0,14416321}` x3 2x in place; `{46a006b0,14416324}` x1 2x in place; `{46a006b0,14416325}` x1 2x in place; `{46a006b0,14416326}` x1 2x in place.
- `imagerect=` doubled (3):
  - GZWinBMP `(0,0,216,155)` -> `(0,0,324,233)`
  - GZWinBMP `(13,11,216,155)` -> `(20,17,324,233)`
  - GZWinBMP `(0,112,216,155)` -> `(0,168,324,233)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `RegionLauncherCityName` x1 -> `0xaa8cdfb1` (32 px ini, was 16); `RegionLauncherFunds` x1 -> `0xaa8cdfb4` (28 px ini, was 14).

### Existing-city bubble (`I-ca539340`, source `T-00000000_G-96a006b0_I-ca539340.ui`)

- Root 0x89e1567c id=0x0a551c50: area `(146,71,404,321)` -> `(219,107,606,482)` (258x250 -> 387x375).
  NOTE: tail-anchored popup -- the GAME positions it (tail at the clicked
  tile), so the doubled origin is irrelevant; only the doubled SIZE is the
  assertion. Its body+tail bubble art `{46a006b0,14416322}` IS among the doubled TGIs (see
  the art plan), split across two BMPs whose `imagerect` slices were
  doubled with it.
- `area=` rects doubled: 23 (every one in the script; 23 controls total).
- Art refs: `{46a006b0,14015586}` x3 2x in place; `{46a006b0,14416322}` x3 2x in place; `{46a006b0,14416323}` x1 2x in place; `{46a006b0,14416324}` x1 2x in place; `{46a006b0,14416325}` x1 2x in place; `{46a006b0,14416326}` x1 2x in place; `{46a006b0,cbfb3730}` x1 2x in place; `{46a006b0,cbfb3731}` x1 2x in place; `{46a006b0,cbfb3732}` x1 2x in place.
- `imagerect=` doubled (6):
  - GZWinBMP `(0,0,258,239)` -> `(0,0,387,359)`
  - GZWinBMP `(12,10,258,239)` -> `(18,15,387,359)`
  - GZWinBMP `(0,196,258,239)` -> `(0,294,387,359)`
  - GZWinBMP `(0,0,11,11)` -> `(0,0,17,17)`
  - GZWinBMP `(0,0,22,11)` -> `(0,0,33,17)`
  - GZWinBMP `(0,0,33,11)` -> `(0,0,50,17)`
- 7 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `RegionLauncherCityName` x1 -> `0xaa8cdfb1` (32 px ini, was 16); `RegionLauncherFunds` x2 -> `0xaa8cdfb4` (28 px ini, was 14); `RegionLauncherMR` x1 -> `0xaa8cdfb5` (28 px ini, was 14); `RegionLauncherMayorName` x1 -> `0xaa8cdfb2` (28 px ini, was 14); `RegionLauncherPop` x3 -> `0xaa8cdfb3` (26 px ini, was 13).

### Photo Album (`I-4a8cc5ea`, source `T-00000000_G-96a006b0_I-4a8cc5ea.ui`)

- Root GZWinGen id=0x0a8cd3ee: area `(251,179,934,761)` -> `(377,269,1401,1142)` (683x582 -> 1024x873).
- `area=` rects doubled: 25 (every one in the script; 25 controls total).
- Art refs: `{1abe787d,144161e4}` x1 2x in place; `{1abe787d,144161ee}` x1 2x in place; `{1abe787d,14416270}` x3 2x in place; `{1abe787d,14416271}` x1 2x in place; `{1abe787d,14416272}` x1 2x in place; `{1abe787d,14416273}` x1 2x in place; `{46a006b0,14015586}` x1 2x in place; `{46a006b0,144161eb}` x2 2x in place; `{46a006b0,e2b66db8}` x1 -> clone.
- `imagerect=` doubled (3):
  - GZWinBMP `(6,6,563,386)` -> `(9,9,845,579)`
  - GZWinBMP `(6,34,563,386)` -> `(9,51,845,579)`
  - GZWinBMP `(12,22,78,78)` -> `(18,33,117,117)`
- 9 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyLight` x1 -> `0x4a809918` (26 px ini, was 13); `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x3 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x2 -> `0x4a809916` (36 px ini, was 18).

### Delete City confirm (`I-8a5ab1d0`, source `T-00000000_G-96a006b0_I-8a5ab1d0.ui`)

- Root GZWinGen id=0x8a5ab1d0: area `(251,180,553,308)` -> `(377,270,830,462)` (302x128 -> 453x192).
- `area=` rects doubled: 7 (every one in the script; 7 controls total).
- Art refs: `{1abe787d,14416240}` x2 2x in place; `{46a006b0,144161eb}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(12,35,180,180)` -> `(18,53,270,270)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16).

### City Import (`I-8a5ab1cd`, source `T-00000000_G-96a006b0_I-8a5ab1cd.ui`)

- Root GZWinGen id=0x0a5ba192: area `(251,180,581,368)` -> `(377,270,872,552)` (330x188 -> 495x282).
- `area=` rects doubled: 10 (every one in the script; 10 controls total).
- Art refs: `{1abe787d,144161e4}` x1 2x in place; `{1abe787d,144161ee}` x1 2x in place; `{46a006b0,144161eb}` x2 2x in place; `{46a006b0,144161ee}` x1 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
  - GZWinBMP `(12,38,180,180)` -> `(18,57,270,270)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenButton` x2 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x3 -> `0x4a809916` (36 px ini, was 18).

### Generic message box (code-driven confirms) (`I-ea8cc3c6`, source `T-00000000_G-96a006b0_I-ea8cc3c6.ui`)

- Root GZWinGen id=0x8a8dfcf5: area `(251,180,615,372)` -> `(377,270,923,558)` (364x192 -> 546x288).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{1abe787d,144161e4}` x1 2x in place; `{1abe787d,144161ee}` x2 2x in place; `{46a006b0,144161eb}` x2 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
  - GZWinBMP `(22,35,180,180)` -> `(33,53,270,270)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Credits (`I-ca551016`, source `T-00000000_G-96a006b0_I-ca551016.ui`)

- Root GZWinGen id=0x0a592004: area `(121,45,646,329)` -> `(182,68,969,494)` (525x284 -> 787x426).
- `area=` rects doubled: 7 (every one in the script; 7 controls total).
- Art refs: `{46a006b0,13e14fb7}` x3 2x in place; `{46a006b0,144161eb}` x1 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(15,6,525,284)` -> `(23,9,788,426)`
  - GZWinBMP `(15,35,525,284)` -> `(23,53,788,426)`
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Advisor toast (salmon) (`I-4a5a89d4`, source `T-00000000_G-96a006b0_I-4a5a89d4.ui`)

- Root GZWinGen id=0x4a9db60c: area `(395,377,845,623)` -> `(593,566,1268,935)` (450x246 -> 675x369).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161f1}` x1 2x in place; `{46a006b0,144161f3}` x1 2x in place; `{46a006b0,144161f5}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,85,94)` -> `(0,0,128,141)`
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `BdgtSummaryCurrentBal` x1 -> `0xea85d300` (34 px ini, was 17).

### Advisor toast (salmon B) (`I-4a5a89d5`, source `T-00000000_G-96a006b0_I-4a5a89d5.ui`)

- Root GZWinGen id=0x4a9db60c: area `(395,377,845,623)` -> `(593,566,1268,935)` (450x246 -> 675x369).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161f2}` x1 2x in place; `{46a006b0,144161f4}` x1 2x in place; `{46a006b0,144161f6}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,87,94)` -> `(0,0,131,141)`
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenButton` x1 -> `0x4a809919` (32 px ini, was 16).

### Advisor toast (green) (`I-2bb16d50`, source `T-00000000_G-96a006b0_I-2bb16d50.ui`)

- Root GZWinGen id=0xebb16d71: area `(395,377,845,623)` -> `(593,566,1268,935)` (450x246 -> 675x369).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,2bc3ac85}` x1 2x in place; `{46a006b0,4bc3a5ae}` x3 2x in place; `{46a006b0,8bc38238}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,87,94)` -> `(0,0,131,141)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `BdgtSummaryCurrentBal` x3 -> `0xea85d300` (34 px ini, was 17).

### Advisor toast (blue) (`I-0bbc06b6`, source `T-00000000_G-96a006b0_I-0bbc06b6.ui`)

- Root GZWinGen id=0xebbc081e: area `(395,377,845,623)` -> `(593,566,1268,935)` (450x246 -> 675x369).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161f2}` x1 2x in place; `{46a006b0,144161f4}` x1 2x in place; `{46a006b0,144161f6}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,87,94)` -> `(0,0,131,141)`
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `BdgtSummaryCurrentBal` x1 -> `0xea85d300` (34 px ini, was 17).

### Advisor toast (peach) (`I-4bbc080f`, source `T-00000000_G-96a006b0_I-4bbc080f.ui`)

- Root GZWinGen id=0xebbc081e: area `(403,385,853,631)` -> `(605,578,1280,947)` (450x246 -> 675x369).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161f1}` x1 2x in place; `{46a006b0,144161f3}` x1 2x in place; `{46a006b0,144161f5}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,87,94)` -> `(0,0,131,141)`
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `BdgtSummaryCurrentBal` x1 -> `0xea85d300` (34 px ini, was 17).

### Building query (residential) (`I-ca56783a`, source `T-00000000_G-96a006b0_I-ca56783a.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,536)` -> `(369,303,807,804)` (292x334 -> 438x501).
- `area=` rects doubled: 28 (every one in the script; 28 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,1441620e}` x1 2x in place; `{46a006b0,14416222}` x2 2x in place; `{46a006b0,14416245}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,12,32)` -> `(0,0,18,48)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x21 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Building query (tall variant) (`I-4a5672bf`, source `T-00000000_G-96a006b0_I-4a5672bf.ui`)

- Root GZWinGen id=0x10000005: area `(257,74,549,517)` -> `(386,111,824,776)` (292x443 -> 438x665).
- `area=` rects doubled: 39 (every one in the script; 39 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,1441620e}` x1 2x in place; `{46a006b0,14416228}` x2 2x in place; `{46a006b0,1441622c}` x1 2x in place; `{46a006b0,14416245}` x1 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(0,0,12,32)` -> `(0,0,18,48)`
  - GZWinBMP `(0,0,42,48)` -> `(0,0,63,72)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x30 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Building query (short variant) (`I-2a567dc1`, source `T-00000000_G-96a006b0_I-2a567dc1.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,538)` -> `(369,303,807,807)` (292x336 -> 438x504).
- `area=` rects doubled: 28 (every one in the script; 28 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,1441620e}` x1 2x in place; `{46a006b0,14416226}` x2 2x in place; `{46a006b0,14416245}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,12,32)` -> `(0,0,18,48)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x21 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Obliterate City confirm (`I-2a41436c`, source `T-00000000_G-96a006b0_I-2a41436c.ui`)

- Root GZWinGen id=0x27df05be: area `(100,68,439,268)` -> `(150,102,659,402)` (339x200 -> 509x300).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161ee}` x3 2x in place; `{46a006b0,e2b66db8}` x2 -> clone.
- `imagerect=` doubled (2):
  - GZWinBMP `(14,5,180,180)` -> `(21,8,270,270)`
  - GZWinBMP `(12,38,180,180)` -> `(18,57,270,270)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyLight` x1 -> `0x4a809918` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Reconcile Edges (boundaries match) (`I-0a4d0c43`, source `T-00000000_G-96a006b0_I-0a4d0c43.ui`)

- Root GZWinGen id=0x6a4d0a59: area `(131,62,488,214)` -> `(197,93,732,321)` (357x152 -> 535x228).
- `area=` rects doubled: 5 (every one in the script; 5 controls total).
- Art refs: `{1abe787d,144161ee}` x1 2x in place; `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416240}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(12,37,180,180)` -> `(18,56,270,270)`
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16).

### Reconcile Edges (highlighted areas confirm) (`I-ca4d0b22`, source `T-00000000_G-96a006b0_I-ca4d0b22.ui`)

- Root GZWinGen id=0x6a4d0a59: area `(131,62,488,219)` -> `(197,93,732,329)` (357x157 -> 535x236).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{1abe787d,144161ee}` x1 2x in place; `{46a006b0,144161eb}` x2 2x in place; `{46a006b0,14416240}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(12,37,180,180)` -> `(18,56,270,270)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16).

### Reconcile Edges (variant 3) (`I-8a4d0a17`, source `T-00000000_G-96a006b0_I-8a4d0a17.ui`)

- Root GZWinGen id=0x6a4d0a59: area `(131,62,488,244)` -> `(197,93,732,366)` (357x182 -> 535x273).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x2 2x in place; `{46a006b0,14416240}` x2 2x in place; `{46a006b0,14416245}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(12,22,180,180)` -> `(18,33,270,270)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyLight` x1 -> `0x4a809918` (26 px ini, was 13); `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16).

### Exit to Region confirm (in-city, 3-btn) (`I-6a553aa4`, source `T-00000000_G-96a006b0_I-6a553aa4.ui`)

- Root GZWinGen id=0xaa921f4f: area `(332,232,602,393)` -> `(498,348,903,590)` (270x161 -> 405x242).
- `area=` rects doubled: 5 (every one in the script; 5 controls total).
- Art refs: `{46a006b0,144161e4}` x1 2x in place; `{46a006b0,144161eb}` x3 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenButton` x3 -> `0x4a809919` (32 px ini, was 16).

### Quit confirm (in-city, 3-btn) (`I-0a55161d`, source `T-00000000_G-96a006b0_I-0a55161d.ui`)

- Root GZWinGen id=0xaa921f4f: area `(332,232,662,389)` -> `(498,348,993,584)` (330x157 -> 495x236).
- `area=` rects doubled: 5 (every one in the script; 5 controls total).
- Art refs: `{46a006b0,144161e4}` x1 2x in place; `{46a006b0,144161eb}` x3 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenButton` x3 -> `0x4a809919` (32 px ini, was 16).

### Exit to Region (in-city, play-city variant) (`I-eaaeec1b`, source `T-00000000_G-96a006b0_I-eaaeec1b.ui`)

- Root GZWinGen id=0x6aaeec4a: area `(332,232,662,389)` -> `(498,348,993,584)` (330x157 -> 495x236).
- `area=` rects doubled: 5 (every one in the script; 5 controls total).
- Art refs: `{46a006b0,144161e4}` x1 2x in place; `{46a006b0,144161eb}` x3 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenButton` x3 -> `0x4a809919` (32 px ini, was 16).

### Can't-save-during-disaster confirm (`I-4a89b3f2`, source `T-00000000_G-96a006b0_I-4a89b3f2.ui`)

- Root GZWinGen id=0x2a96ed21: area `(251,180,551,308)` -> `(377,270,827,462)` (300x128 -> 450x192).
- `area=` rects doubled: 7 (every one in the script; 7 controls total).
- Art refs: `{1abe787d,14416240}` x1 2x in place; `{46a006b0,144161eb}` x2 2x in place; `{46a006b0,14416240}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(12,22,180,180)` -> `(18,33,270,270)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16).

### Establish City (`I-2a41436b`, source `T-00000000_G-96a006b0_I-2a41436b.ui`)

- Root GZWinGen id=0x6a414973: area `(75,47,509,281)` -> `(113,71,764,422)` (434x234 -> 651x351).
- `area=` rects doubled: 19 (every one in the script; 19 controls total).
- Art refs: `{1abe787d,14416246}` x3 2x in place; `{46a006b0,144161e4}` x1 2x in place; `{46a006b0,144161ee}` x2 2x in place; `{46a006b0,14416243}` x1 2x in place; `{46a006b0,e2b66db8}` x2 -> clone.
- `imagerect=` doubled (3):
  - GZWinBMP `(10,10,78,78)` -> `(15,15,117,117)`
  - GZWinBMP `(30,35,180,180)` -> `(45,53,270,270)`
  - GZWinBMP `(0,0,44,37)` -> `(0,0,66,56)`
- 6 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyLight` x3 -> `0x4a809918` (26 px ini, was 13); `GenBodyMedium` x6 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Select A My Sim (Sim-mode sim picker) (`I-0a243d80`, source `T-00000000_G-96a006b0_I-0a243d80.ui`)

- Root GZWinGen id=0x6a243d9e: area `(200,100,634,481)` -> `(300,150,951,722)` (434x381 -> 651x572).
- `area=` rects doubled: 86 (every one in the script; 86 controls total).
- Art refs: `{1abe787d,14416240}` x2 2x in place; `{46a006b0,13f15250}` x3 2x in place; `{46a006b0,13f15251}` x1 2x in place; `{46a006b0,13f15253}` x1 2x in place; `{46a006b0,13f15254}` x1 2x in place; `{46a006b0,13f15255}` x1 2x in place; `{46a006b0,13f15257}` x1 2x in place; `{46a006b0,13f15258}` x1 2x in place; `{46a006b0,13f15259}` x1 2x in place; `{46a006b0,13f1525e}` x22 2x in place; `{46a006b0,13f1525f}` x12 2x in place; `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,e2b66db8}` x2 -> clone; `{46a006b0,ea32f104}` x22 LEFT 1x.
- `imagerect=` doubled (3):
  - GZWinBMP `(10,5,434,381)` -> `(15,8,651,572)`
  - GZWinBMP `(80,284,434,381)` -> `(120,426,651,572)`
  - GZWinBMP `(12,32,180,180)` -> `(18,48,270,270)`
- 46 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyLight` x2 -> `0x4a809918` (26 px ini, was 13); `GenBodyMedium` x5 -> `0x4a809917` (26 px ini, was 13); `GenButton` x3 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `MySimPageNum` x12 -> `0x6a8f4293` (32 px ini, was 16).
- Controls left fully 1x (no 2x asset): GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`; GZWinBMP `{46a006b0,ea32f104}`.

### U-Drive-It Select vehicle for <MySim> (`I-4bf325e8`, source `T-00000000_G-96a006b0_I-4bf325e8.ui`)

- Root GZWinGen id=0xcbf32603: area `(205,54,639,501)` -> `(308,81,959,752)` (434x447 -> 651x671).
- `area=` rects doubled: 75 (every one in the script; 75 controls total).
- Art refs: `{46a006b0,13f15258}` x1 2x in place; `{46a006b0,13f15259}` x1 2x in place; `{46a006b0,13f1525f}` x6 2x in place; `{46a006b0,144161f9}` x1 2x in place; `{46a006b0,2c201cb0}` x1 2x in place; `{46a006b0,2c201cb1}` x1 2x in place; `{46a006b0,2c201cb2}` x1 2x in place; `{46a006b0,4bfc52c2}` x28 2x in place; `{46a006b0,6b998f30}` x1 LEFT 1x; `{46a006b0,cbbab0ae}` x2 2x in place; `{46a006b0,cbec3db2}` x1 2x in place; `{46a006b0,e2b66db8}` x2 -> clone; `{46a006b0,ea32f104}` x27 LEFT 1x.
- `imagerect=` doubled (29):
  - GZWinBMP `(10,5,384,361)` -> `(15,8,576,542)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
- 44 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenButton` x2 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x2 -> `0x4a809916` (36 px ini, was 18); `MySimPageNum` x6 -> `0x6a8f4293` (32 px ini, was 16).

### U-Drive-It Select pedestrian style (`I-abfaef15`, source `T-00000000_G-96a006b0_I-abfaef15.ui`)

- Root GZWinGen id=0xcbf32603: area `(206,52,640,351)` -> `(309,78,960,527)` (434x299 -> 651x449).
- `area=` rects doubled: 44 (every one in the script; 44 controls total).
- Art refs: `{46a006b0,13f15258}` x1 2x in place; `{46a006b0,13f15259}` x1 2x in place; `{46a006b0,13f1525f}` x6 2x in place; `{46a006b0,144161f9}` x1 2x in place; `{46a006b0,4bfc52c2}` x14 2x in place; `{46a006b0,6b998f30}` x1 LEFT 1x; `{46a006b0,cbbab0ae}` x2 2x in place; `{46a006b0,cbec3db2}` x1 2x in place; `{46a006b0,e2b66db8}` x2 -> clone; `{46a006b0,ea32f104}` x13 LEFT 1x.
- `imagerect=` doubled (15):
  - GZWinBMP `(10,5,384,361)` -> `(15,8,576,542)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
  - GZWinBMP `(0,0,42,42)` -> `(0,0,63,63)`
- 27 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenButton` x2 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x2 -> `0x4a809916` (36 px ini, was 18); `MySimPageNum` x6 -> `0x6a8f4293` (32 px ini, was 16).

### Missing plugin-packs warning (city load) (`I-ea89b6c3`, source `T-00000000_G-96a006b0_I-ea89b6c3.ui`)

- Root GZWinGen id=0x2a5cfb2c: area `(45,49,400,287)` -> `(68,74,600,431)` (355x238 -> 532x357).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{1abe787d,144161e4}` x1 2x in place; `{1abe787d,144161ee}` x1 2x in place; `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,144161ee}` x1 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
  - GZWinBMP `(12,38,180,180)` -> `(18,57,270,270)`
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyLight` x1 -> `0x4a809918` (26 px ini, was 13); `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Generic one-button notification popup (`I-ca8cbf0f`, source `T-00000000_G-96a006b0_I-ca8cbf0f.ui`)

- Root GZWinGen id=0xaa8def97: area `(251,180,551,346)` -> `(377,270,827,519)` (300x166 -> 450x249).
- `area=` rects doubled: 7 (every one in the script; 7 controls total).
- Art refs: `{1abe787d,144161e4}` x1 2x in place; `{1abe787d,144161ee}` x2 2x in place; `{46a006b0,144161eb}` x1 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
  - GZWinBMP `(22,35,180,180)` -> `(33,53,270,270)`
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Select A Bridge (network across water) (`I-ebd0d36c`, source `T-00000000_G-96a006b0_I-ebd0d36c.ui`)

- Root GZWinGen id=0x0c525b9e: area `(594,17,1005,388)` -> `(891,26,1508,582)` (411x371 -> 617x556).
- `area=` rects doubled: 18 (every one in the script; 18 controls total).
- Art refs: `{1abe787d,0c0e0f3c}` x1 2x in place; `{1abe787d,8c0e0f2d}` x1 2x in place; `{46a006b0,144161eb}` x2 2x in place; `{46a006b0,46a006a6}` x1 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,85,50)` -> `(0,0,128,75)`
- 5 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `ButtonLabel` x5 -> `0x68963c54` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Tutorial page (also an HTML-fed pane - see list D) (`I-0a2dd355`, source `T-00000000_G-96a006b0_I-0a2dd355.ui`)

- Root GZWinGen id=0x4a35b0f2: area `(334,6,807,314)` -> `(501,9,1211,471)` (473x308 -> 710x462).
- `area=` rects doubled: 5 (every one in the script; 5 controls total).
- Art refs: `{46a006b0,144161eb}` x2 2x in place; `{46a006b0,14416280}` x1 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenButton` x2 -> `0x4a809919` (32 px ini, was 16).

### Tutorial exit confirm (`I-6a5e73c0`, source `T-00000000_G-96a006b0_I-6a5e73c0.ui`)

- Root GZWinGen id=0xea5e748c: area `(300,255,630,368)` -> `(450,383,945,552)` (330x113 -> 495x169).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x2 2x in place; `{46a006b0,14416240}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(12,37,180,180)` -> `(18,56,270,270)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x2 -> `0x4a809919` (32 px ini, was 16).

### Game Over / Run for Senator (`I-0a5cf71d`, source `T-00000000_G-96a006b0_I-0a5cf71d.ui`)

- Root GZWinGen id=0x2a5cfb2c: area `(45,49,400,267)` -> `(68,74,600,401)` (355x218 -> 532x327).
- `area=` rects doubled: 7 (every one in the script; 7 controls total).
- Art refs: `{46a006b0,144161e4}` x1 2x in place; `{46a006b0,144161ee}` x2 2x in place; `{46a006b0,e2b66db8}` x1 -> clone.
- `imagerect=` doubled (2):
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
  - GZWinBMP `(12,37,180,180)` -> `(18,56,270,270)`
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Startup splash 768x600 (`I-8aa9aa14`, source `T-00000000_G-96a006b0_I-8aa9aa14.ui`)

- Root GZWinGen id=0xaaa9c9d9: area `(0,0,768,600)` -> `(0,0,1152,900)` (768x600 -> 1152x900).
- `area=` rects doubled: 4 (every one in the script; 4 controls total).
- Art refs: `{46a006b0,ea7f0eae}` x1 LEFT 1x.
- `imagerect=` doubled: none present on 2x-art controls.
- Fonts converted: `Heading3` x1 -> `0xe9c86b2d` (34 px ini, was 17); `NewsBody` x1 -> `0xeadd276d` (28 px ini, was 14); `NewsHeader` x1 -> `0xeadd276c` (28 px ini, was 14).
- Controls left fully 1x (no 2x asset): GZWinGen `{46a006b0,ea7f0eae}`.

### Startup splash 800x600 (`I-aaaaf3d1`, source `T-00000000_G-96a006b0_I-aaaaf3d1.ui`)

- Root GZWinGen id=0xaaa9c9d9: area `(0,0,800,600)` -> `(0,0,1200,900)` (800x600 -> 1200x900).
- `area=` rects doubled: 2 (every one in the script; 2 controls total).
- Art refs: `{46a006b0,ea7f0eaf}` x1 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 1 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `WindowTitle` x1 -> `0xe2b14587` (38 px ini, was 19).

### Clock time popup (`I-aa5e60d1`, source `T-00000000_G-96a006b0_I-aa5e60d1.ui`)

- Root GZWinGen id=0xca5e6261: area `(30,32,122,62)` -> `(45,48,183,93)` (92x30 -> 138x45).
- `area=` rects doubled: 4 (every one in the script; 4 controls total).
- Art refs: `{46a006b0,144161e7}` x1 2x in place; `{46a006b0,46a006a4}` x1 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 2 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: none (no name-form font tokens).

### Label Tool (map annotation) (`I-6b704690`, source `T-00000000_G-96a006b0_I-6b704690.ui`)

- Root GZWinGen id=0x8a8dfcf5: area `(250,180,659,322)` -> `(375,270,989,483)` (409x142 -> 614x213).
- `area=` rects doubled: 10 (every one in the script; 10 controls total).
- Art refs: `{1abe787d,144161e4}` x1 2x in place; `{1abe787d,144161ee}` x2 2x in place; `{46a006b0,144161eb}` x3 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(12,12,78,78)` -> `(18,18,117,117)`
  - GZWinBMP `(22,35,180,180)` -> `(33,53,270,270)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyLight` x1 -> `0x4a809918` (26 px ini, was 13); `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x3 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Region city-bubble stub (narrow) (`I-ca539343`, source `T-00000000_G-96a006b0_I-ca539343.ui`)

- Root GZWinGen id=0x0a551c53: area `(146,71,188,230)` -> `(219,107,282,345)` (42x159 -> 63x238).
- `area=` rects doubled: 3 (every one in the script; 3 controls total).
- Art refs: `{46a006b0,14416231}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,42,65)` -> `(0,0,63,98)`
- 1 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: none (no name-form font tokens).

### Select A Bridge sibling button (`I-ebd0d36d`, source `T-00000000_G-96a006b0_I-ebd0d36d.ui`)

- Root GZWinGen id=0x000a0000: area `(22,18,111,76)` -> `(33,27,167,114)` (89x58 -> 134x87).
- `area=` rects doubled: 2 (every one in the script; 2 controls total).
- Art refs: .
- `imagerect=` doubled: none present on 2x-art controls.
- Fonts converted: `ButtonLabel` x1 -> `0x68963c54` (26 px ini, was 13).

### Text Entry prompt (Save City confirm) (`I-e9263d4c`, source `T-00000000_G-96a006b0_I-e9263d4c.ui`)

- Root GZWinGen id=0xc9264be2: area `(240,79,559,192)` -> `(360,119,839,288)` (319x113 -> 479x169).
- `area=` rects doubled: 3 (every one in the script; 3 controls total).
- Art refs: `{46a006b0,e2b66db8}` x1 -> clone.
- `imagerect=` doubled: none present on 2x-art controls.
- 1 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: none (no name-form font tokens).

### Set Lot Size (`I-e9263de5`, source `T-00000000_G-96a006b0_I-e9263de5.ui`)

- Root GZWinGen id=0x8926eebe: area `(254,81,503,173)` -> `(381,122,755,260)` (249x92 -> 374x138).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,e2b66db8}` x1 -> clone.
- `imagerect=` doubled: none present on 2x-art controls.
- 1 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `main9` x2 -> `0x00006e4f` (24 px ini, was 12).

### Query panel 0a562a05 (`I-0a562a05`, source `T-00000000_G-96a006b0_I-0a562a05.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,322)` -> `(369,303,807,483)` (292x120 -> 438x180).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{1abe787d,14416224}` x2 2x in place; `{46a006b0,144161eb}` x1 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 0a8b819e (`I-0a8b819e`, source `T-00000000_G-96a006b0_I-0a8b819e.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,405)` -> `(369,303,807,608)` (292x203 -> 438x305).
- `area=` rects doubled: 14 (every one in the script; 14 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416212}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x9 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 0a8b98fe (`I-0a8b98fe`, source `T-00000000_G-96a006b0_I-0a8b98fe.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 0a8b9a67 (`I-0a8b9a67`, source `T-00000000_G-96a006b0_I-0a8b9a67.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 0a8b9c43 (`I-0a8b9c43`, source `T-00000000_G-96a006b0_I-0a8b9c43.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 0a8b9c6a (`I-0a8b9c6a`, source `T-00000000_G-96a006b0_I-0a8b9c6a.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 0c1d56e4 (`I-0c1d56e4`, source `T-00000000_G-96a006b0_I-0c1d56e4.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,410)` -> `(0,0,318,615)` (212x410 -> 318x615).
- `area=` rects doubled: 35 (every one in the script; 35 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980eb}` x1 2x in place; `{46a006b0,cc1a735d}` x9 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 15 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x19 -> `0x4a809912` (22 px ini, was 11).

### Query panel 0c1d730b (`I-0c1d730b`, source `T-00000000_G-96a006b0_I-0c1d730b.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,375)` -> `(0,0,318,563)` (212x375 -> 318x563).
- `area=` rects doubled: 31 (every one in the script; 31 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980ec}` x1 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x15 -> `0x4a809912` (22 px ini, was 11).

### Query panel 0c1d7737 (`I-0c1d7737`, source `T-00000000_G-96a006b0_I-0c1d7737.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,320)` -> `(0,0,318,480)` (212x320 -> 318x480).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel 0c1d7974 (`I-0c1d7974`, source `T-00000000_G-96a006b0_I-0c1d7974.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,305)` -> `(0,0,318,458)` (212x305 -> 318x458).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980ec}` x1 2x in place; `{46a006b0,cc1a735d}` x5 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 11 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `GenSubHeader` x1 -> `0x4a80991a` (32 px ini, was 16); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x10 -> `0x4a809912` (22 px ini, was 11).

### Query panel 0c1d79ac (`I-0c1d79ac`, source `T-00000000_G-96a006b0_I-0c1d79ac.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,300)` -> `(0,0,318,450)` (212x300 -> 318x450).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x6 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 12 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x12 -> `0x4a809912` (22 px ini, was 11).

### Query panel 0c1d7b60 (`I-0c1d7b60`, source `T-00000000_G-96a006b0_I-0c1d7b60.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,340)` -> `(0,0,318,510)` (212x340 -> 318x510).
- `area=` rects doubled: 31 (every one in the script; 31 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x8 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 14 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x16 -> `0x4a809912` (22 px ini, was 11).

### Query panel 0c1d7e71 (`I-0c1d7e71`, source `T-00000000_G-96a006b0_I-0c1d7e71.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,370)` -> `(0,0,318,555)` (212x370 -> 318x555).
- `area=` rects doubled: 33 (every one in the script; 33 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x9 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 15 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x18 -> `0x4a809912` (22 px ini, was 11).

### Query panel 0c1d81fc (`I-0c1d81fc`, source `T-00000000_G-96a006b0_I-0c1d81fc.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,350)` -> `(0,0,318,525)` (212x350 -> 318x525).
- `area=` rects doubled: 33 (every one in the script; 33 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980ec}` x1 2x in place; `{46a006b0,cc1a735d}` x8 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 14 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x17 -> `0x4a809912` (22 px ini, was 11).

### Query panel 2a554f6d (`I-2a554f6d`, source `T-00000000_G-96a006b0_I-2a554f6d.ui`)

- Root GZWinGen id=0x10000005: area `(246,201,538,485)` -> `(369,302,807,728)` (292x284 -> 438x426).
- `area=` rects doubled: 21 (every one in the script; 21 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416212}` x1 2x in place; `{46a006b0,14416227}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x15 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 2a5621ee (`I-2a5621ee`, source `T-00000000_G-96a006b0_I-2a5621ee.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,383)` -> `(369,303,807,575)` (292x181 -> 438x272).
- `area=` rects doubled: 12 (every one in the script; 12 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416217}` x1 2x in place; `{46a006b0,1441622a}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x7 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 2a564884 (`I-2a564884`, source `T-00000000_G-96a006b0_I-2a564884.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,427)` -> `(369,303,807,641)` (292x225 -> 438x338).
- `area=` rects doubled: 15 (every one in the script; 15 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416210}` x1 2x in place; `{46a006b0,14416221}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x9 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 2a56675c (`I-2a56675c`, source `T-00000000_G-96a006b0_I-2a56675c.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,340)` -> `(369,303,807,510)` (292x138 -> 438x207).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416221}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 2a5e7490 (`I-2a5e7490`, source `T-00000000_G-96a006b0_I-2a5e7490.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,748,415)` -> `(369,303,1122,623)` (502x213 -> 753x320).
- `area=` rects doubled: 30 (every one in the script; 30 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416220}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x24 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x2 -> `0x4a809916` (36 px ini, was 18).

### Query panel 2a8b7e1c (`I-2a8b7e1c`, source `T-00000000_G-96a006b0_I-2a8b7e1c.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,444)` -> `(369,303,807,666)` (292x242 -> 438x363).
- `area=` rects doubled: 17 (every one in the script; 17 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416210}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x11 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 2a8b97c1 (`I-2a8b97c1`, source `T-00000000_G-96a006b0_I-2a8b97c1.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 2a8b99d0 (`I-2a8b99d0`, source `T-00000000_G-96a006b0_I-2a8b99d0.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 2a8b9df2 (`I-2a8b9df2`, source `T-00000000_G-96a006b0_I-2a8b9df2.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 2c02ba84 (`I-2c02ba84`, source `T-00000000_G-96a006b0_I-2c02ba84.ui`)

- Root 0x89e1567c id=0x10000006: area `(187,53,403,189)` -> `(281,80,605,284)` (216x136 -> 324x204).
- `area=` rects doubled: 9 (every one in the script; 9 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,4c02b518}` x1 2x in place; `{46a006b0,4c0f0d31}` x1 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 6 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13).

### Query panel 2c096de6 (`I-2c096de6`, source `T-00000000_G-96a006b0_I-2c096de6.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 2c1d73cb (`I-2c1d73cb`, source `T-00000000_G-96a006b0_I-2c1d73cb.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,325)` -> `(0,0,318,488)` (212x325 -> 318x488).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel 2c1d784b (`I-2c1d784b`, source `T-00000000_G-96a006b0_I-2c1d784b.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,325)` -> `(0,0,318,488)` (212x325 -> 318x488).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel 2c1d8024 (`I-2c1d8024`, source `T-00000000_G-96a006b0_I-2c1d8024.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,320)` -> `(0,0,318,480)` (212x320 -> 318x480).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel 4a562da5 (`I-4a562da5`, source `T-00000000_G-96a006b0_I-4a562da5.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,407)` -> `(369,303,807,611)` (292x205 -> 438x308).
- `area=` rects doubled: 14 (every one in the script; 14 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416215}` x1 2x in place; `{46a006b0,14416229}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x9 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4a565d13 (`I-4a565d13`, source `T-00000000_G-96a006b0_I-4a565d13.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,413)` -> `(369,303,807,620)` (292x211 -> 438x317).
- `area=` rects doubled: 16 (every one in the script; 16 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,1441621b}` x1 2x in place; `{46a006b0,14416229}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x11 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4a5665eb (`I-4a5665eb`, source `T-00000000_G-96a006b0_I-4a5665eb.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416229}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4a566c14 (`I-4a566c14`, source `T-00000000_G-96a006b0_I-4a566c14.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,407)` -> `(369,303,807,611)` (292x205 -> 438x308).
- `area=` rects doubled: 16 (every one in the script; 16 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416220}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x12 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4a566d6e (`I-4a566d6e`, source `T-00000000_G-96a006b0_I-4a566d6e.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,412)` -> `(369,303,807,618)` (292x210 -> 438x315).
- `area=` rects doubled: 16 (every one in the script; 16 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416220}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x12 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4a5e7ed3 (`I-4a5e7ed3`, source `T-00000000_G-96a006b0_I-4a5e7ed3.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,748,374)` -> `(369,303,1122,561)` (502x172 -> 753x258).
- `area=` rects doubled: 18 (every one in the script; 18 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416220}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x12 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x2 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4a8b7fe7 (`I-4a8b7fe7`, source `T-00000000_G-96a006b0_I-4a8b7fe7.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,444)` -> `(369,303,807,666)` (292x242 -> 438x363).
- `area=` rects doubled: 17 (every one in the script; 17 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416210}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x11 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4a8b9396 (`I-4a8b9396`, source `T-00000000_G-96a006b0_I-4a8b9396.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4a8b9936 (`I-4a8b9936`, source `T-00000000_G-96a006b0_I-4a8b9936.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4a8b9c92 (`I-4a8b9c92`, source `T-00000000_G-96a006b0_I-4a8b9c92.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4a8b9dab (`I-4a8b9dab`, source `T-00000000_G-96a006b0_I-4a8b9dab.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4c0969e2 (`I-4c0969e2`, source `T-00000000_G-96a006b0_I-4c0969e2.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 4c1a68d2 (`I-4c1a68d2`, source `T-00000000_G-96a006b0_I-4c1a68d2.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,345)` -> `(0,0,318,518)` (212x345 -> 318x518).
- `area=` rects doubled: 31 (every one in the script; 31 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x8 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 14 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x16 -> `0x4a809912` (22 px ini, was 11).

### Query panel 4c1d78f7 (`I-4c1d78f7`, source `T-00000000_G-96a006b0_I-4c1d78f7.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,330)` -> `(0,0,318,495)` (212x330 -> 318x495).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980ec}` x1 2x in place; `{46a006b0,cc1a735d}` x6 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 12 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x13 -> `0x4a809912` (22 px ini, was 11).

### Query panel 4c1d7c0c (`I-4c1d7c0c`, source `T-00000000_G-96a006b0_I-4c1d7c0c.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,320)` -> `(0,0,318,480)` (212x320 -> 318x480).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel 4c1d7c65 (`I-4c1d7c65`, source `T-00000000_G-96a006b0_I-4c1d7c65.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,355)` -> `(0,0,318,533)` (212x355 -> 318x533).
- `area=` rects doubled: 33 (every one in the script; 33 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980eb}` x1 2x in place; `{46a006b0,cc1980ec}` x1 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x16 -> `0x4a809912` (22 px ini, was 11).

### Query panel 4c1d7d40 (`I-4c1d7d40`, source `T-00000000_G-96a006b0_I-4c1d7d40.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,350)` -> `(0,0,318,525)` (212x350 -> 318x525).
- `area=` rects doubled: 31 (every one in the script; 31 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x8 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 14 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x16 -> `0x4a809912` (22 px ini, was 11).

### Query panel 4c47800e (`I-4c47800e`, source `T-00000000_G-96a006b0_I-4c47800e.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,423)` -> `(369,303,807,635)` (292x221 -> 438x332).
- `area=` rects doubled: 16 (every one in the script; 16 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,1441620f}` x1 2x in place; `{46a006b0,14416229}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x11 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 6a51506f (`I-6a51506f`, source `T-00000000_G-96a006b0_I-6a51506f.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,412)` -> `(369,303,807,618)` (292x210 -> 438x315).
- `area=` rects doubled: 11 (every one in the script; 11 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416211}` x1 2x in place; `{46a006b0,14416223}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x5 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 6a555a84 (`I-6a555a84`, source `T-00000000_G-96a006b0_I-6a555a84.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,423)` -> `(369,303,807,635)` (292x221 -> 438x332).
- `area=` rects doubled: 15 (every one in the script; 15 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416210}` x1 2x in place; `{46a006b0,14416221}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x9 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 6a561b3a (`I-6a561b3a`, source `T-00000000_G-96a006b0_I-6a561b3a.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,425)` -> `(369,303,807,638)` (292x223 -> 438x335).
- `area=` rects doubled: 16 (every one in the script; 16 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416214}` x1 2x in place; `{46a006b0,14416229}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x11 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 6a562f56 (`I-6a562f56`, source `T-00000000_G-96a006b0_I-6a562f56.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,485)` -> `(369,303,807,728)` (292x283 -> 438x425).
- `area=` rects doubled: 23 (every one in the script; 23 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416218}` x1 2x in place; `{46a006b0,1441622a}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x17 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 6a566151 (`I-6a566151`, source `T-00000000_G-96a006b0_I-6a566151.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,423)` -> `(369,303,807,635)` (292x221 -> 438x332).
- `area=` rects doubled: 16 (every one in the script; 16 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,1441621a}` x1 2x in place; `{46a006b0,14416229}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x11 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 6a8b9875 (`I-6a8b9875`, source `T-00000000_G-96a006b0_I-6a8b9875.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 6a8b9acc (`I-6a8b9acc`, source `T-00000000_G-96a006b0_I-6a8b9acc.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 6a8b9af3 (`I-6a8b9af3`, source `T-00000000_G-96a006b0_I-6a8b9af3.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 6c1d789a (`I-6c1d789a`, source `T-00000000_G-96a006b0_I-6c1d789a.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,340)` -> `(0,0,318,510)` (212x340 -> 318x510).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel 6c1d7ac3 (`I-6c1d7ac3`, source `T-00000000_G-96a006b0_I-6c1d7ac3.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,340)` -> `(0,0,318,510)` (212x340 -> 318x510).
- `area=` rects doubled: 31 (every one in the script; 31 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x8 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 14 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x16 -> `0x4a809912` (22 px ini, was 11).

### Query panel 6c1d7f5c (`I-6c1d7f5c`, source `T-00000000_G-96a006b0_I-6c1d7f5c.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,305)` -> `(0,0,318,458)` (212x305 -> 318x458).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980ec}` x1 2x in place; `{46a006b0,cc1a735d}` x5 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 11 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `GenSubHeader` x1 -> `0x4a80991a` (32 px ini, was 16); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x10 -> `0x4a809912` (22 px ini, was 11).

### Query panel 6c1d8057 (`I-6c1d8057`, source `T-00000000_G-96a006b0_I-6c1d8057.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,320)` -> `(0,0,318,480)` (212x320 -> 318x480).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel 8a554483 (`I-8a554483`, source `T-00000000_G-96a006b0_I-8a554483.ui`)

- Root GZWinGen id=0x10000005: area `(570,200,862,474)` -> `(855,300,1293,711)` (292x274 -> 438x411).
- `area=` rects doubled: 18 (every one in the script; 18 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416210}` x1 2x in place; `{46a006b0,14416221}` x2 2x in place; `{46a006b0,46a006a7}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 5 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x11 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 8a5e7bd2 (`I-8a5e7bd2`, source `T-00000000_G-96a006b0_I-8a5e7bd2.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,748,415)` -> `(369,303,1122,623)` (502x213 -> 753x320).
- `area=` rects doubled: 30 (every one in the script; 30 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416220}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x24 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x2 -> `0x4a809916` (36 px ini, was 18).

### Query panel 8a8b95b0 (`I-8a8b95b0`, source `T-00000000_G-96a006b0_I-8a8b95b0.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 8a8b9811 (`I-8a8b9811`, source `T-00000000_G-96a006b0_I-8a8b9811.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 8a8b98a7 (`I-8a8b98a7`, source `T-00000000_G-96a006b0_I-8a8b98a7.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 8a8b9d12 (`I-8a8b9d12`, source `T-00000000_G-96a006b0_I-8a8b9d12.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 8a948d49 (`I-8a948d49`, source `T-00000000_G-96a006b0_I-8a948d49.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,346)` -> `(369,303,807,519)` (292x144 -> 438x216).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416219}` x1 2x in place; `{46a006b0,1441622a}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel 8c1d7423 (`I-8c1d7423`, source `T-00000000_G-96a006b0_I-8c1d7423.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,353)` -> `(0,0,318,530)` (212x353 -> 318x530).
- `area=` rects doubled: 31 (every one in the script; 31 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x8 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 14 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x17 -> `0x4a809912` (22 px ini, was 11).

### Query panel 8c1d76d5 (`I-8c1d76d5`, source `T-00000000_G-96a006b0_I-8c1d76d5.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,300)` -> `(0,0,318,450)` (212x300 -> 318x450).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x6 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 12 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x12 -> `0x4a809912` (22 px ini, was 11).

### Query panel 8c3bd047 (`I-8c3bd047`, source `T-00000000_G-96a006b0_I-8c3bd047.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,320)` -> `(0,0,318,480)` (212x320 -> 318x480).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel aa554aea (`I-aa554aea`, source `T-00000000_G-96a006b0_I-aa554aea.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,431)` -> `(369,303,807,647)` (292x229 -> 438x344).
- `area=` rects doubled: 18 (every one in the script; 18 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416216}` x1 2x in place; `{46a006b0,14416221}` x2 2x in place; `{46a006b0,46a006a7}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 5 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x11 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel aa555346 (`I-aa555346`, source `T-00000000_G-96a006b0_I-aa555346.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,384)` -> `(369,303,807,576)` (292x182 -> 438x273).
- `area=` rects doubled: 12 (every one in the script; 12 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416212}` x1 2x in place; `{46a006b0,14416227}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x7 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel aa561f93 (`I-aa561f93`, source `T-00000000_G-96a006b0_I-aa561f93.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,362)` -> `(369,303,807,543)` (292x160 -> 438x240).
- `area=` rects doubled: 10 (every one in the script; 10 controls total).
- Art refs: `{1abe787d,14416220}` x2 2x in place; `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416217}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x5 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel aa565036 (`I-aa565036`, source `T-00000000_G-96a006b0_I-aa565036.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,412)` -> `(369,303,807,618)` (292x210 -> 438x315).
- `area=` rects doubled: 13 (every one in the script; 13 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416210}` x1 2x in place; `{46a006b0,14416221}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x7 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel aa565f5b (`I-aa565f5b`, source `T-00000000_G-96a006b0_I-aa565f5b.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416229}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel aa5661eb (`I-aa5661eb`, source `T-00000000_G-96a006b0_I-aa5661eb.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,413)` -> `(369,303,807,620)` (292x211 -> 438x317).
- `area=` rects doubled: 16 (every one in the script; 16 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,1441621c}` x1 2x in place; `{46a006b0,14416229}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x11 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel aa5bef41 (`I-aa5bef41`, source `T-00000000_G-96a006b0_I-aa5bef41.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,367)` -> `(369,303,807,551)` (292x165 -> 438x248).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416217}` x1 2x in place; `{46a006b0,1441622a}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x3 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel aa5e14cc (`I-aa5e14cc`, source `T-00000000_G-96a006b0_I-aa5e14cc.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,748,416)` -> `(369,303,1122,624)` (502x214 -> 753x321).
- `area=` rects doubled: 30 (every one in the script; 30 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416220}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x24 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x2 -> `0x4a809916` (36 px ini, was 18).

### Query panel aa8b9755 (`I-aa8b9755`, source `T-00000000_G-96a006b0_I-aa8b9755.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel aa8b9971 (`I-aa8b9971`, source `T-00000000_G-96a006b0_I-aa8b9971.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel aa8b999e (`I-aa8b999e`, source `T-00000000_G-96a006b0_I-aa8b999e.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ac096ac7 (`I-ac096ac7`, source `T-00000000_G-96a006b0_I-ac096ac7.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ac1d544d (`I-ac1d544d`, source `T-00000000_G-96a006b0_I-ac1d544d.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,325)` -> `(0,0,318,488)` (212x325 -> 318x488).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel ac1d7548 (`I-ac1d7548`, source `T-00000000_G-96a006b0_I-ac1d7548.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,375)` -> `(0,0,318,563)` (212x375 -> 318x563).
- `area=` rects doubled: 31 (every one in the script; 31 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x8 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 14 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x1 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x17 -> `0x4a809912` (22 px ini, was 11).

### Query panel ac1d7a81 (`I-ac1d7a81`, source `T-00000000_G-96a006b0_I-ac1d7a81.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,310)` -> `(0,0,318,465)` (212x310 -> 318x465).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980ec}` x1 2x in place; `{46a006b0,cc1a735d}` x5 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 11 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `GenSubHeader` x1 -> `0x4a80991a` (32 px ini, was 16); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x10 -> `0x4a809912` (22 px ini, was 11).

### Query panel ac3b72f6 (`I-ac3b72f6`, source `T-00000000_G-96a006b0_I-ac3b72f6.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,423)` -> `(369,303,807,635)` (292x221 -> 438x332).
- `area=` rects doubled: 16 (every one in the script; 16 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,1441621a}` x1 2x in place; `{46a006b0,14416229}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x11 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ca566f94 (`I-ca566f94`, source `T-00000000_G-96a006b0_I-ca566f94.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,432)` -> `(369,303,807,648)` (292x230 -> 438x345).
- `area=` rects doubled: 18 (every one in the script; 18 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416220}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x14 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ca8b8408 (`I-ca8b8408`, source `T-00000000_G-96a006b0_I-ca8b8408.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,454)` -> `(369,303,807,681)` (292x252 -> 438x378).
- `area=` rects doubled: 19 (every one in the script; 19 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416216}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x13 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ca8b8564 (`I-ca8b8564`, source `T-00000000_G-96a006b0_I-ca8b8564.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,396)` -> `(369,303,807,594)` (292x194 -> 438x291).
- `area=` rects doubled: 14 (every one in the script; 14 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416210}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x9 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ca8b96c2 (`I-ca8b96c2`, source `T-00000000_G-96a006b0_I-ca8b96c2.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ca8b9845 (`I-ca8b9845`, source `T-00000000_G-96a006b0_I-ca8b9845.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ca8b9aa2 (`I-ca8b9aa2`, source `T-00000000_G-96a006b0_I-ca8b9aa2.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 6 (every one in the script; 6 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ca8b9ce7 (`I-ca8b9ce7`, source `T-00000000_G-96a006b0_I-ca8b9ce7.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ca8b9d40 (`I-ca8b9d40`, source `T-00000000_G-96a006b0_I-ca8b9d40.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel cc097fc0 (`I-cc097fc0`, source `T-00000000_G-96a006b0_I-cc097fc0.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel cc1d71d3 (`I-cc1d71d3`, source `T-00000000_G-96a006b0_I-cc1d71d3.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,320)` -> `(0,0,318,480)` (212x320 -> 318x480).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel cc1d72a2 (`I-cc1d72a2`, source `T-00000000_G-96a006b0_I-cc1d72a2.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,325)` -> `(0,0,318,488)` (212x325 -> 318x488).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel cc1d778b (`I-cc1d778b`, source `T-00000000_G-96a006b0_I-cc1d778b.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,320)` -> `(0,0,318,480)` (212x320 -> 318x480).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel cc1d7a1f (`I-cc1d7a1f`, source `T-00000000_G-96a006b0_I-cc1d7a1f.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,300)` -> `(0,0,318,450)` (212x300 -> 318x450).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x6 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 12 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x12 -> `0x4a809912` (22 px ini, was 11).

### Query panel cc1d824f (`I-cc1d824f`, source `T-00000000_G-96a006b0_I-cc1d824f.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,300)` -> `(0,0,318,450)` (212x300 -> 318x450).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x6 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 12 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x12 -> `0x4a809912` (22 px ini, was 11).

### Query panel cc313f17 (`I-cc313f17`, source `T-00000000_G-96a006b0_I-cc313f17.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,395)` -> `(369,303,807,593)` (292x193 -> 438x290).
- `area=` rects doubled: 12 (every one in the script; 12 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416215}` x1 2x in place; `{46a006b0,14416229}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x7 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel cc44f885 (`I-cc44f885`, source `T-00000000_G-96a006b0_I-cc44f885.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,320)` -> `(0,0,318,480)` (212x320 -> 318x480).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

### Query panel ea5655e4 (`I-ea5655e4`, source `T-00000000_G-96a006b0_I-ea5655e4.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,485)` -> `(369,303,807,728)` (292x283 -> 438x425).
- `area=` rects doubled: 21 (every one in the script; 21 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416218}` x1 2x in place; `{46a006b0,1441622a}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x15 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ea565970 (`I-ea565970`, source `T-00000000_G-96a006b0_I-ea565970.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,477)` -> `(369,303,807,716)` (292x275 -> 438x413).
- `area=` rects doubled: 22 (every one in the script; 22 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416219}` x1 2x in place; `{46a006b0,1441622a}` x2 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x17 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ea566a49 (`I-ea566a49`, source `T-00000000_G-96a006b0_I-ea566a49.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,374)` -> `(369,303,807,561)` (292x172 -> 438x258).
- `area=` rects doubled: 10 (every one in the script; 10 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416220}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x6 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ea8b82db (`I-ea8b82db`, source `T-00000000_G-96a006b0_I-ea8b82db.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,457)` -> `(369,303,807,686)` (292x255 -> 438x383).
- `area=` rects doubled: 19 (every one in the script; 19 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416210}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place; `{46a006b0,46a006a7}` x1 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,24,44)` -> `(0,0,36,66)`
- 4 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x13 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ec096e72 (`I-ec096e72`, source `T-00000000_G-96a006b0_I-ec096e72.ui`)

- Root GZWinGen id=0x10000005: area `(246,202,538,336)` -> `(369,303,807,504)` (292x134 -> 438x201).
- `area=` rects doubled: 8 (every one in the script; 8 controls total).
- Art refs: `{46a006b0,144161eb}` x1 2x in place; `{46a006b0,14416225}` x2 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 3 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x4 -> `0x4a809917` (26 px ini, was 13); `GenButton` x1 -> `0x4a809919` (32 px ini, was 16); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18).

### Query panel ec1a73ba (`I-ec1a73ba`, source `T-00000000_G-96a006b0_I-ec1a73ba.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,380)` -> `(0,0,318,570)` (212x380 -> 318x570).
- `area=` rects doubled: 39 (every one in the script; 39 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980eb}` x1 2x in place; `{46a006b0,cc1980ec}` x1 2x in place; `{46a006b0,cc1a735d}` x10 2x in place.
- `imagerect=` doubled (2):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 16 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x22 -> `0x4a809912` (22 px ini, was 11).

### Query panel ec1d74d5 (`I-ec1d74d5`, source `T-00000000_G-96a006b0_I-ec1d74d5.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,310)` -> `(0,0,318,465)` (212x310 -> 318x465).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x6 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 12 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x12 -> `0x4a809912` (22 px ini, was 11).

### Query panel ec1d7599 (`I-ec1d7599`, source `T-00000000_G-96a006b0_I-ec1d7599.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,305)` -> `(0,0,318,458)` (212x305 -> 318x458).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x6 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 12 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x12 -> `0x4a809912` (22 px ini, was 11).

### Query panel ec1d75e2 (`I-ec1d75e2`, source `T-00000000_G-96a006b0_I-ec1d75e2.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,305)` -> `(0,0,318,458)` (212x305 -> 318x458).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980ec}` x1 2x in place; `{46a006b0,cc1a735d}` x5 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 11 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `GenSubHeader` x1 -> `0x4a80991a` (32 px ini, was 16); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x10 -> `0x4a809912` (22 px ini, was 11).

### Query panel ec1d77dd (`I-ec1d77dd`, source `T-00000000_G-96a006b0_I-ec1d77dd.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,330)` -> `(0,0,318,495)` (212x330 -> 318x495).
- `area=` rects doubled: 31 (every one in the script; 31 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1980ec}` x1 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled (1):
  - GZWinBMP `(0,0,14,29)` -> `(0,0,21,44)`
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x15 -> `0x4a809912` (22 px ini, was 11).

### Query panel ec1d79d7 (`I-ec1d79d7`, source `T-00000000_G-96a006b0_I-ec1d79d7.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,360)` -> `(0,0,318,540)` (212x360 -> 318x540).
- `area=` rects doubled: 31 (every one in the script; 31 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x8 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 14 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x16 -> `0x4a809912` (22 px ini, was 11).

### Query panel ec1d7a56 (`I-ec1d7a56`, source `T-00000000_G-96a006b0_I-ec1d7a56.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,300)` -> `(0,0,318,450)` (212x300 -> 318x450).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x6 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 12 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x12 -> `0x4a809912` (22 px ini, was 11).

### Query panel ec1d7efe (`I-ec1d7efe`, source `T-00000000_G-96a006b0_I-ec1d7efe.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,300)` -> `(0,0,318,450)` (212x300 -> 318x450).
- `area=` rects doubled: 27 (every one in the script; 27 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x6 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 12 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x12 -> `0x4a809912` (22 px ini, was 11).

### Query panel ec1d8125 (`I-ec1d8125`, source `T-00000000_G-96a006b0_I-ec1d8125.ui`)

- Root 0x89e1567c id=0x10000006: area `(0,0,212,320)` -> `(0,0,318,480)` (212x320 -> 318x480).
- `area=` rects doubled: 29 (every one in the script; 29 controls total).
- Art refs: `{46a006b0,144161e0}` x1 2x in place; `{46a006b0,144161e2}` x1 2x in place; `{46a006b0,144161e4}` x2 2x in place; `{46a006b0,144161f9}` x2 2x in place; `{46a006b0,cc1a735d}` x7 2x in place.
- `imagerect=` doubled: none present on 2x-art controls.
- 13 control(s) with 2x art but no `imagerect` (edge-slice frames /
  button state strips -- the engine fits cells to the control area;
  self-adapting, eyeball frame thickness in-game).
- Fonts converted: `GenBodyMedium` x2 -> `0x4a809917` (26 px ini, was 13); `GenHeader` x1 -> `0x4a809916` (36 px ini, was 18); `Heading4` x1 -> `0xe9c86b58` (30 px ini, was 15); `PUckDate` x14 -> `0x4a809912` (22 px ini, was 11).

## Expected on-screen result (2400x1600 table)

| Dialog | 1x root | 1.5x root | Note |
|---|---|---|---|
| Move In My Sim marker (green+red, #191) | 46x97 at (109,151) | **69x145** at (164,227) |  |
| Play Options | 699x523 at (0,0) | **1049x785** at (0,0) | root gen larger than visible dialog art |
| Audio Options | 330x471 at (44,20) | **495x707** at (66,30) |  |
| Graphic Options | 722x558 at (3,0) | **1083x837** at (5,0) | root gen larger than visible dialog art |
| Region Name (Create Region) | 330x168 at (251,180) | **495x252** at (377,270) |  |
| Delete Region confirm | 300x158 at (251,180) | **450x237** at (377,270) |  |
| Load Region | 330x188 at (171,103) | **495x282** at (257,155) |  |
| Quit confirm (region screen) | 330x109 at (332,170) | **495x164** at (498,255) |  |
| Quit confirm (are-you-sure) | 313x128 at (251,180) | **469x192** at (377,270) |  |
| Start New City bubble | 216x165 at (146,71) | **324x247** at (219,107) | game-positioned (tail anchor); size-only assertion |
| Existing-city bubble | 258x250 at (146,71) | **387x375** at (219,107) | game-positioned (tail anchor); size-only assertion |
| Photo Album | 683x582 at (251,179) | **1024x873** at (377,269) |  |
| Delete City confirm | 302x128 at (251,180) | **453x192** at (377,270) |  |
| City Import | 330x188 at (251,180) | **495x282** at (377,270) |  |
| Generic message box (code-driven confirms) | 364x192 at (251,180) | **546x288** at (377,270) |  |
| Credits | 525x284 at (121,45) | **787x426** at (182,68) |  |
| Advisor toast (salmon) | 450x246 at (395,377) | **675x369** at (593,566) |  |
| Advisor toast (salmon B) | 450x246 at (395,377) | **675x369** at (593,566) |  |
| Advisor toast (green) | 450x246 at (395,377) | **675x369** at (593,566) |  |
| Advisor toast (blue) | 450x246 at (395,377) | **675x369** at (593,566) |  |
| Advisor toast (peach) | 450x246 at (403,385) | **675x369** at (605,578) |  |
| Building query (residential) | 292x334 at (246,202) | **438x501** at (369,303) |  |
| Building query (tall variant) | 292x443 at (257,74) | **438x665** at (386,111) |  |
| Building query (short variant) | 292x336 at (246,202) | **438x504** at (369,303) |  |
| Obliterate City confirm | 339x200 at (100,68) | **509x300** at (150,102) |  |
| Reconcile Edges (boundaries match) | 357x152 at (131,62) | **535x228** at (197,93) |  |
| Reconcile Edges (highlighted areas confirm) | 357x157 at (131,62) | **535x236** at (197,93) |  |
| Reconcile Edges (variant 3) | 357x182 at (131,62) | **535x273** at (197,93) |  |
| Exit to Region confirm (in-city, 3-btn) | 270x161 at (332,232) | **405x242** at (498,348) |  |
| Quit confirm (in-city, 3-btn) | 330x157 at (332,232) | **495x236** at (498,348) |  |
| Exit to Region (in-city, play-city variant) | 330x157 at (332,232) | **495x236** at (498,348) |  |
| Can't-save-during-disaster confirm | 300x128 at (251,180) | **450x192** at (377,270) |  |
| Establish City | 434x234 at (75,47) | **651x351** at (113,71) |  |
| Select A My Sim (Sim-mode sim picker) | 434x381 at (200,100) | **651x572** at (300,150) |  |
| U-Drive-It Select vehicle for <MySim> | 434x447 at (205,54) | **651x671** at (308,81) |  |
| U-Drive-It Select pedestrian style | 434x299 at (206,52) | **651x449** at (309,78) |  |
| Missing plugin-packs warning (city load) | 355x238 at (45,49) | **532x357** at (68,74) |  |
| Generic one-button notification popup | 300x166 at (251,180) | **450x249** at (377,270) |  |
| Select A Bridge (network across water) | 411x371 at (594,17) | **617x556** at (891,26) |  |
| Tutorial page (also an HTML-fed pane - see list D) | 473x308 at (334,6) | **710x462** at (501,9) |  |
| Tutorial exit confirm | 330x113 at (300,255) | **495x169** at (450,383) |  |
| Game Over / Run for Senator | 355x218 at (45,49) | **532x327** at (68,74) |  |
| Startup splash 768x600 | 768x600 at (0,0) | **1152x900** at (0,0) |  |
| Startup splash 800x600 | 800x600 at (0,0) | **1200x900** at (0,0) |  |
| Clock time popup | 92x30 at (30,32) | **138x45** at (45,48) |  |
| Label Tool (map annotation) | 409x142 at (250,180) | **614x213** at (375,270) |  |
| Region city-bubble stub (narrow) | 42x159 at (146,71) | **63x238** at (219,107) |  |
| Select A Bridge sibling button | 89x58 at (22,18) | **134x87** at (33,27) |  |
| Text Entry prompt (Save City confirm) | 319x113 at (240,79) | **479x169** at (360,119) |  |
| Set Lot Size | 249x92 at (254,81) | **374x138** at (381,122) |  |
| Query panel 0a562a05 | 292x120 at (246,202) | **438x180** at (369,303) |  |
| Query panel 0a8b819e | 292x203 at (246,202) | **438x305** at (369,303) |  |
| Query panel 0a8b98fe | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 0a8b9a67 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 0a8b9c43 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 0a8b9c6a | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 0c1d56e4 | 212x410 at (0,0) | **318x615** at (0,0) |  |
| Query panel 0c1d730b | 212x375 at (0,0) | **318x563** at (0,0) |  |
| Query panel 0c1d7737 | 212x320 at (0,0) | **318x480** at (0,0) |  |
| Query panel 0c1d7974 | 212x305 at (0,0) | **318x458** at (0,0) |  |
| Query panel 0c1d79ac | 212x300 at (0,0) | **318x450** at (0,0) |  |
| Query panel 0c1d7b60 | 212x340 at (0,0) | **318x510** at (0,0) |  |
| Query panel 0c1d7e71 | 212x370 at (0,0) | **318x555** at (0,0) |  |
| Query panel 0c1d81fc | 212x350 at (0,0) | **318x525** at (0,0) |  |
| Query panel 2a554f6d | 292x284 at (246,201) | **438x426** at (369,302) |  |
| Query panel 2a5621ee | 292x181 at (246,202) | **438x272** at (369,303) |  |
| Query panel 2a564884 | 292x225 at (246,202) | **438x338** at (369,303) |  |
| Query panel 2a56675c | 292x138 at (246,202) | **438x207** at (369,303) |  |
| Query panel 2a5e7490 | 502x213 at (246,202) | **753x320** at (369,303) |  |
| Query panel 2a8b7e1c | 292x242 at (246,202) | **438x363** at (369,303) |  |
| Query panel 2a8b97c1 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 2a8b99d0 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 2a8b9df2 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 2c02ba84 | 216x136 at (187,53) | **324x204** at (281,80) |  |
| Query panel 2c096de6 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 2c1d73cb | 212x325 at (0,0) | **318x488** at (0,0) |  |
| Query panel 2c1d784b | 212x325 at (0,0) | **318x488** at (0,0) |  |
| Query panel 2c1d8024 | 212x320 at (0,0) | **318x480** at (0,0) |  |
| Query panel 4a562da5 | 292x205 at (246,202) | **438x308** at (369,303) |  |
| Query panel 4a565d13 | 292x211 at (246,202) | **438x317** at (369,303) |  |
| Query panel 4a5665eb | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 4a566c14 | 292x205 at (246,202) | **438x308** at (369,303) |  |
| Query panel 4a566d6e | 292x210 at (246,202) | **438x315** at (369,303) |  |
| Query panel 4a5e7ed3 | 502x172 at (246,202) | **753x258** at (369,303) |  |
| Query panel 4a8b7fe7 | 292x242 at (246,202) | **438x363** at (369,303) |  |
| Query panel 4a8b9396 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 4a8b9936 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 4a8b9c92 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 4a8b9dab | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 4c0969e2 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 4c1a68d2 | 212x345 at (0,0) | **318x518** at (0,0) |  |
| Query panel 4c1d78f7 | 212x330 at (0,0) | **318x495** at (0,0) |  |
| Query panel 4c1d7c0c | 212x320 at (0,0) | **318x480** at (0,0) |  |
| Query panel 4c1d7c65 | 212x355 at (0,0) | **318x533** at (0,0) |  |
| Query panel 4c1d7d40 | 212x350 at (0,0) | **318x525** at (0,0) |  |
| Query panel 4c47800e | 292x221 at (246,202) | **438x332** at (369,303) |  |
| Query panel 6a51506f | 292x210 at (246,202) | **438x315** at (369,303) |  |
| Query panel 6a555a84 | 292x221 at (246,202) | **438x332** at (369,303) |  |
| Query panel 6a561b3a | 292x223 at (246,202) | **438x335** at (369,303) |  |
| Query panel 6a562f56 | 292x283 at (246,202) | **438x425** at (369,303) |  |
| Query panel 6a566151 | 292x221 at (246,202) | **438x332** at (369,303) |  |
| Query panel 6a8b9875 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 6a8b9acc | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 6a8b9af3 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 6c1d789a | 212x340 at (0,0) | **318x510** at (0,0) |  |
| Query panel 6c1d7ac3 | 212x340 at (0,0) | **318x510** at (0,0) |  |
| Query panel 6c1d7f5c | 212x305 at (0,0) | **318x458** at (0,0) |  |
| Query panel 6c1d8057 | 212x320 at (0,0) | **318x480** at (0,0) |  |
| Query panel 8a554483 | 292x274 at (570,200) | **438x411** at (855,300) |  |
| Query panel 8a5e7bd2 | 502x213 at (246,202) | **753x320** at (369,303) |  |
| Query panel 8a8b95b0 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 8a8b9811 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 8a8b98a7 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 8a8b9d12 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel 8a948d49 | 292x144 at (246,202) | **438x216** at (369,303) |  |
| Query panel 8c1d7423 | 212x353 at (0,0) | **318x530** at (0,0) |  |
| Query panel 8c1d76d5 | 212x300 at (0,0) | **318x450** at (0,0) |  |
| Query panel 8c3bd047 | 212x320 at (0,0) | **318x480** at (0,0) |  |
| Query panel aa554aea | 292x229 at (246,202) | **438x344** at (369,303) |  |
| Query panel aa555346 | 292x182 at (246,202) | **438x273** at (369,303) |  |
| Query panel aa561f93 | 292x160 at (246,202) | **438x240** at (369,303) |  |
| Query panel aa565036 | 292x210 at (246,202) | **438x315** at (369,303) |  |
| Query panel aa565f5b | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel aa5661eb | 292x211 at (246,202) | **438x317** at (369,303) |  |
| Query panel aa5bef41 | 292x165 at (246,202) | **438x248** at (369,303) |  |
| Query panel aa5e14cc | 502x214 at (246,202) | **753x321** at (369,303) |  |
| Query panel aa8b9755 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel aa8b9971 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel aa8b999e | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel ac096ac7 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel ac1d544d | 212x325 at (0,0) | **318x488** at (0,0) |  |
| Query panel ac1d7548 | 212x375 at (0,0) | **318x563** at (0,0) |  |
| Query panel ac1d7a81 | 212x310 at (0,0) | **318x465** at (0,0) |  |
| Query panel ac3b72f6 | 292x221 at (246,202) | **438x332** at (369,303) |  |
| Query panel ca566f94 | 292x230 at (246,202) | **438x345** at (369,303) |  |
| Query panel ca8b8408 | 292x252 at (246,202) | **438x378** at (369,303) |  |
| Query panel ca8b8564 | 292x194 at (246,202) | **438x291** at (369,303) |  |
| Query panel ca8b96c2 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel ca8b9845 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel ca8b9aa2 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel ca8b9ce7 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel ca8b9d40 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel cc097fc0 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel cc1d71d3 | 212x320 at (0,0) | **318x480** at (0,0) |  |
| Query panel cc1d72a2 | 212x325 at (0,0) | **318x488** at (0,0) |  |
| Query panel cc1d778b | 212x320 at (0,0) | **318x480** at (0,0) |  |
| Query panel cc1d7a1f | 212x300 at (0,0) | **318x450** at (0,0) |  |
| Query panel cc1d824f | 212x300 at (0,0) | **318x450** at (0,0) |  |
| Query panel cc313f17 | 292x193 at (246,202) | **438x290** at (369,303) |  |
| Query panel cc44f885 | 212x320 at (0,0) | **318x480** at (0,0) |  |
| Query panel ea5655e4 | 292x283 at (246,202) | **438x425** at (369,303) |  |
| Query panel ea565970 | 292x275 at (246,202) | **438x413** at (369,303) |  |
| Query panel ea566a49 | 292x172 at (246,202) | **438x258** at (369,303) |  |
| Query panel ea8b82db | 292x255 at (246,202) | **438x383** at (369,303) |  |
| Query panel ec096e72 | 292x134 at (246,202) | **438x201** at (369,303) |  |
| Query panel ec1a73ba | 212x380 at (0,0) | **318x570** at (0,0) |  |
| Query panel ec1d74d5 | 212x310 at (0,0) | **318x465** at (0,0) |  |
| Query panel ec1d7599 | 212x305 at (0,0) | **318x458** at (0,0) |  |
| Query panel ec1d75e2 | 212x305 at (0,0) | **318x458** at (0,0) |  |
| Query panel ec1d77dd | 212x330 at (0,0) | **318x495** at (0,0) |  |
| Query panel ec1d79d7 | 212x360 at (0,0) | **318x540** at (0,0) |  |
| Query panel ec1d7a56 | 212x300 at (0,0) | **318x450** at (0,0) |  |
| Query panel ec1d7efe | 212x300 at (0,0) | **318x450** at (0,0) |  |
| Query panel ec1d8125 | 212x320 at (0,0) | **318x480** at (0,0) |  |

- GZWinGen dialog roots are positioned by the game's dialog-open code, so final
  placement may be re-centered by the game -- the SIZE is the assertion, the
  origin is best-effort.
- Frame/title-bar 9-slice art and button strips render from the 2x clones (or
  in-place 2x art) with doubled `imagerect` insets where the script carried any.
- Every OTHER dialog in the game keeps the untouched 1x originals: shared art is
  isolated behind new-TGI clones; the only in-place 2x art is exclusive to these
  six scripts.
- Captions render at 1.5x sizes via GUID font binding + the deployed 1.5x-scaled
  FontStyle table (FontStyle-15x.ini), whose [Font Styles] sizes = round(1x * 1.5). The dialog
  scripts only bind styles by GUID; the sizes come from that loose FontStyle file.

## Interop / preconditions

- No TGI overlap with `z_SC4UIScale_SelectiveArt.dat`: selective-safe ships none
  of these 164 .UI scripts (checked against its stage + refmap scaled sets), and
  every clone IID here was collision-checked against its planned clones (1 fell
  back to `^ 0x53430002` for exactly that reason). The two dats coexist.
- Runtime scaling/docking of the region-dialog roots (UiSpike kRegionDialogDocks:
  0x000a0000, 0x0a551c50, 0x0a551c53, 0x0a592004, 0x0a5ba192, 0x0a8cd3ee, 0x0c525b9e, 0x10000005, 0x10000006, 0x27df05be, 0x27df05bf, 0x2a57cb82, 0x2a57db82, 0x2a5cfb2c, 0x2a96ed21, 0x4a35b0f2, 0x4a5ba0e7, 0x4a9db60c, 0x6a243d9e, 0x6a414973, 0x6a4d0a59, 0x6a5ba20c, 0x6aaeec4a, 0x8926eebe, 0x8a5ab1d0, 0x8a8dfcf5, 0xaa8def97, 0xaa921f4f, 0xaaa9c9d9, 0xc9264be2, 0xca5e6261, 0xcbf32603, 0xea53f5db, 0xea5ba0d1, 0xea5e748c, 0xebb16d71, 0xebbc081e)
  must remain disabled, or the dialogs get doubled twice.
- The doubled FontStyle.ini must be deployed (it is) for the font step to show.

## Revert

Delete `z_SC4UIScale_DialogStatic.dat` from the Plugins folder it was copied to.
That is the whole footprint: the package only ADDS same-TGI .UI overrides and
new-TGI PNG clones (plus one exclusive in-place PNG override); no game file is
modified. (Nothing was deployed by the build; the dat lives only in
`tools\dialog-static\` until copied by hand.)
