005a51e0  sub      esp, 0xbc
005a51e6  push     ebp
005a51e7  mov      ebp, dword ptr [esp + 0xc4]
005a51ee  mov      eax, dword ptr [ebp]
005a51f1  push     esi
005a51f2  push     edi
005a51f3  mov      edi, ecx
005a51f5  lea      ecx, [esp + 0x2c]
005a51f9  xor      esi, esi
005a51fb  push     ecx
005a51fc  mov      ecx, ebp
005a51fe  mov      dword ptr [esp + 0x28], edi
005a5202  mov      dword ptr [esp + 0x2c], esi
005a5206  mov      dword ptr [esp + 0x30], esi
005a520a  call     dword ptr [eax + 0x1c]
005a520d  mov      eax, dword ptr [esp + 0x2c]
005a5211  cmp      ax, 3
005a5215  jb       0x5a612d
005a521b  cmp      ax, 4
005a521f  ja       0x5a612d
005a5225  mov      edx, dword ptr [ebp]
005a5228  push     ebx
005a5229  lea      eax, [esp + 0x2c]
005a522d  push     eax
005a522e  mov      ecx, ebp
005a5230  call     dword ptr [edx + 0x1c]
005a5233  mov      edx, dword ptr [ebp]
005a5236  lea      eax, [esp + 0x24]
005a523a  push     eax
005a523b  mov      ecx, ebp
005a523d  call     dword ptr [edx + 0x24]
005a5240  mov      ecx, dword ptr [esp + 0x24]
005a5244  add      edi, 0x3c
005a5247  push     ecx
005a5248  mov      ecx, edi
005a524a  call     0x5a4a80
005a524f  mov      edx, dword ptr [edi + 4]
005a5252  mov      dword ptr [esp + 0x14], esi
005a5256  sub      edx, dword ptr [edi]
005a5258  sar      edx, 2
005a525b  test     edx, edx
005a525d  jbe      0x5a52fa
005a5263  push     0x208
005a5268  call     0x5e55e0
005a526d  add      esp, 4
005a5270  test     eax, eax
005a5272  je       0x5a527f
005a5274  mov      ecx, eax
005a5276  call     0x5b1660
005a527b  mov      ebx, eax
005a527d  jmp      0x5a5281
005a527f  xor      ebx, ebx
005a5281  mov      eax, dword ptr [esp + 0x14]
005a5285  mov      esi, dword ptr [edi]
005a5287  shl      eax, 2
005a528a  add      esi, eax
005a528c  mov      eax, dword ptr [esi]
005a528e  cmp      ebx, eax
005a5290  mov      dword ptr [esp + 0x18], eax
005a5294  je       0x5a52b4
005a5296  test     ebx, ebx
005a5298  je       0x5a52a5
005a529a  mov      ecx, ebx
005a529c  call     0x5af940
005a52a1  mov      eax, dword ptr [esp + 0x18]
005a52a5  test     eax, eax
005a52a7  mov      dword ptr [esi], ebx
005a52a9  je       0x5a52b4
005a52ab  mov      ecx, dword ptr [esp + 0x18]
005a52af  call     0x5b1c80
005a52b4  mov      eax, dword ptr [esp + 0x14]
005a52b8  shl      eax, 2
005a52bb  cmp      word ptr [esp + 0x2c], 1
005a52c1  jne      0x5a52d0
005a52c3  mov      ecx, dword ptr [edi]
005a52c5  mov      ecx, dword ptr [ecx + eax]
005a52c8  push     ebp
005a52c9  call     0x5b0b50
005a52ce  jmp      0x5a52df
005a52d0  mov      edx, dword ptr [edi]
005a52d2  mov      eax, dword ptr [edx + eax]
005a52d5  push     eax
005a52d6  push     ebp
005a52d7  call     0x5b1dc0
005a52dc  add      esp, 8
005a52df  mov      ecx, dword ptr [edi + 4]
005a52e2  mov      ebx, dword ptr [edi]
005a52e4  mov      eax, dword ptr [esp + 0x14]
005a52e8  sub      ecx, ebx
005a52ea  inc      eax
005a52eb  sar      ecx, 2
005a52ee  cmp      eax, ecx
005a52f0  mov      dword ptr [esp + 0x14], eax
005a52f4  jb       0x5a5263
005a52fa  mov      edx, dword ptr [ebp]
005a52fd  lea      eax, [esp + 0x2c]
005a5301  push     eax
005a5302  mov      ecx, ebp
005a5304  call     dword ptr [edx + 0x1c]
005a5307  mov      edx, dword ptr [ebp]
005a530a  lea      eax, [esp + 0x24]
005a530e  push     eax
005a530f  mov      ecx, ebp
005a5311  call     dword ptr [edx + 0x24]
005a5314  mov      esi, dword ptr [esp + 0x28]
005a5318  mov      edi, dword ptr [esp + 0x24]
005a531c  lea      ecx, [esp + 0x68]
005a5320  add      esi, 0x7c
005a5323  call     0x582fe0
005a5328  push     eax
005a5329  push     edi
005a532a  mov      ecx, esi
005a532c  call     0x58adc0
005a5331  mov      eax, dword ptr [esp + 0xa8]
005a5338  test     eax, eax
005a533a  je       0x5a5345
005a533c  push     eax
005a533d  call     0x90cf63
005a5342  add      esp, 4
005a5345  mov      eax, dword ptr [esp + 0x9c]
005a534c  test     eax, eax
005a534e  je       0x5a5359
005a5350  push     eax
005a5351  call     0x90cf63
005a5356  add      esp, 4
005a5359  mov      eax, dword ptr [esp + 0x90]
005a5360  test     eax, eax
005a5362  je       0x5a536d
005a5364  push     eax
005a5365  call     0x90cf63
005a536a  add      esp, 4
005a536d  mov      eax, dword ptr [esp + 0x84]
005a5374  test     eax, eax
005a5376  je       0x5a5381
005a5378  push     eax
005a5379  call     0x90cf63
005a537e  add      esp, 4
005a5381  mov      eax, dword ptr [esp + 0x78]
005a5385  test     eax, eax
005a5387  je       0x5a5392
005a5389  push     eax
005a538a  call     0x90cf63
005a538f  add      esp, 4
005a5392  mov      edx, dword ptr [esi]
005a5394  mov      ecx, dword ptr [esi + 4]
005a5397  sub      ecx, edx
005a5399  mov      eax, 0x51eb851f
005a539e  imul     ecx
005a53a0  sar      edx, 5
005a53a3  mov      ecx, edx
005a53a5  shr      ecx, 0x1f
005a53a8  xor      edi, edi
005a53aa  add      ecx, edx
005a53ac  je       0x5a53de
005a53ae  xor      ebx, ebx
005a53b0  mov      edx, dword ptr [esi]
005a53b2  add      edx, ebx
005a53b4  push     edx
005a53b5  push     ebp
005a53b6  call     0x5a4b50
005a53bb  mov      edx, dword ptr [esi]
005a53bd  mov      ecx, dword ptr [esi + 4]
005a53c0  sub      ecx, edx
005a53c2  mov      eax, 0x51eb851f
005a53c7  imul     ecx
005a53c9  sar      edx, 5
005a53cc  mov      eax, edx
005a53ce  shr      eax, 0x1f
005a53d1  add      esp, 8
005a53d4  inc      edi
005a53d5  add      eax, edx
005a53d7  add      ebx, 0x64
005a53da  cmp      edi, eax
005a53dc  jb       0x5a53b0
005a53de  mov      edx, dword ptr [ebp]
005a53e1  lea      eax, [esp + 0x2c]
005a53e5  push     eax
005a53e6  mov      ecx, ebp
005a53e8  call     dword ptr [edx + 0x1c]
005a53eb  mov      edx, dword ptr [ebp]
005a53ee  lea      eax, [esp + 0x24]
005a53f2  push     eax
005a53f3  mov      ecx, ebp
005a53f5  call     dword ptr [edx + 0x24]
005a53f8  mov      edi, dword ptr [esp + 0x28]
005a53fc  mov      esi, dword ptr [edi + 0xa0]
005a5402  mov      ebx, dword ptr [edi + 0x9c]
005a5408  xor      eax, eax
005a540a  add      edi, 0x9c
005a5410  mov      dword ptr [esp + 0x48], eax
005a5414  mov      dword ptr [esp + 0x4c], eax
005a5418  mov      dword ptr [esp + 0x50], eax
005a541c  mov      dword ptr [esp + 0x54], eax
005a5420  mov      dword ptr [esp + 0x58], eax
005a5424  mov      dword ptr [esp + 0x5c], eax
005a5428  mov      ecx, esi
005a542a  sub      ecx, ebx
005a542c  mov      eax, 0x66666667
005a5431  imul     ecx
005a5433  mov      ecx, dword ptr [esp + 0x24]
005a5437  sar      edx, 4
005a543a  mov      eax, edx
005a543c  shr      eax, 0x1f
005a543f  add      eax, edx
005a5441  cmp      ecx, eax
005a5443  jae      0x5a5473
005a5445  push     0
005a5447  lea      ecx, [ecx + ecx*4]
005a544a  lea      edx, [esp + 0x17]
005a544e  push     edx
005a544f  lea      eax, [ebx + ecx*8]
005a5452  push     eax
005a5453  push     esi
005a5454  push     esi
005a5455  call     0x588560
005a545a  mov      ecx, dword ptr [edi + 4]
005a545d  mov      esi, eax
005a545f  lea      eax, [esp + 0x27]
005a5463  push     eax
005a5464  push     ecx
005a5465  push     esi
005a5466  call     0x587ee0
005a546b  add      esp, 0x20
005a546e  mov      dword ptr [edi + 4], esi
005a5471  jmp      0x5a5483
005a5473  lea      edx, [esp + 0x40]
005a5477  push     edx
005a5478  sub      ecx, eax
005a547a  push     ecx
005a547b  push     esi
005a547c  mov      ecx, edi
005a547e  call     0x589100
005a5483  mov      edx, dword ptr [edi]
005a5485  mov      ecx, dword ptr [edi + 4]
005a5488  sub      ecx, edx
005a548a  mov      eax, 0x66666667
005a548f  imul     ecx
005a5491  sar      edx, 4
005a5494  mov      eax, edx
005a5496  shr      eax, 0x1f
005a5499  xor      ebx, ebx
005a549b  add      eax, edx
005a549d  je       0x5a5524
005a54a3  mov      dword ptr [esp + 0x14], ebx
005a54a7  mov      esi, dword ptr [edi]
005a54a9  mov      ecx, dword ptr [esp + 0x14]
005a54ad  mov      edx, dword ptr [ebp]
005a54b0  add      esi, ecx
005a54b2  push     esi
005a54b3  mov      ecx, ebp
005a54b5  call     dword ptr [edx + 0x30]
005a54b8  mov      eax, dword ptr [ebp]
005a54bb  lea      ecx, [esi + 4]
005a54be  push     ecx
005a54bf  mov      ecx, ebp
005a54c1  call     dword ptr [eax + 0x30]
005a54c4  lea      edx, [esi + 8]
005a54c7  push     edx
005a54c8  push     ebp
005a54c9  call     0x5db4b0
005a54ce  lea      eax, [esi + 0x14]
005a54d1  push     eax
005a54d2  push     ebp
005a54d3  call     0x5db4b0
005a54d8  mov      edx, dword ptr [ebp]
005a54db  add      esp, 0x10
005a54de  lea      eax, [esi + 0x20]
005a54e1  push     eax
005a54e2  mov      ecx, ebp
005a54e4  call     dword ptr [edx + 0x30]
005a54e7  mov      edx, dword ptr [ebp]
005a54ea  lea      eax, [esp + 0x13]
005a54ee  push     eax
005a54ef  mov      ecx, ebp
005a54f1  call     dword ptr [edx + 0x14]
005a54f4  movzx    ecx, byte ptr [esp + 0x13]
005a54f9  mov      dword ptr [esi + 0x24], ecx
005a54fc  mov      ecx, dword ptr [esp + 0x14]
005a5500  mov      eax, dword ptr [edi]
005a5502  add      ecx, 0x28
005a5505  mov      dword ptr [esp + 0x14], ecx
005a5509  mov      ecx, dword ptr [edi + 4]
005a550c  sub      ecx, eax
005a550e  mov      eax, 0x66666667
005a5513  imul     ecx
005a5515  sar      edx, 4
005a5518  mov      eax, edx
005a551a  shr      eax, 0x1f
005a551d  inc      ebx
005a551e  add      eax, edx
005a5520  cmp      ebx, eax
005a5522  jb       0x5a54a7
005a5524  mov      edx, dword ptr [ebp]
005a5527  lea      eax, [esp + 0x2c]
005a552b  push     eax
005a552c  mov      ecx, ebp
005a552e  call     dword ptr [edx + 0x1c]
005a5531  mov      edx, dword ptr [ebp]
005a5534  lea      eax, [esp + 0x24]
005a5538  push     eax
005a5539  mov      ecx, ebp
005a553b  call     dword ptr [edx + 0x24]
005a553e  mov      esi, dword ptr [esp + 0x28]
005a5542  mov      edi, dword ptr [esi + 0xc0]
005a5548  mov      ebx, dword ptr [esi + 0xbc]
005a554e  xor      eax, eax
005a5550  add      esi, 0xbc
005a5556  mov      dword ptr [esp + 0x40], eax
005a555a  mov      dword ptr [esp + 0x44], eax
005a555e  mov      dword ptr [esp + 0x48], eax
005a5562  mov      dword ptr [esp + 0x4c], eax
005a5566  mov      dword ptr [esp + 0x50], eax
005a556a  mov      dword ptr [esp + 0x54], eax
005a556e  mov      ecx, edi
005a5570  sub      ecx, ebx
005a5572  mov      eax, 0x92492493
005a5577  imul     ecx
005a5579  add      edx, ecx
005a557b  mov      ecx, dword ptr [esp + 0x24]
005a557f  sar      edx, 4
005a5582  mov      eax, edx
005a5584  shr      eax, 0x1f
005a5587  add      eax, edx
005a5589  cmp      ecx, eax
005a558b  mov      dword ptr [esp + 0x58], 0x40000000
005a5593  jae      0x5a55ef
005a5595  imul     ecx, ecx, 0x1c
005a5598  push     0
005a559a  lea      edx, [esp + 0x17]
005a559e  push     edx
005a559f  add      ecx, ebx
005a55a1  push     ecx
005a55a2  push     edi
005a55a3  push     edi
005a55a4  call     0x5885d0
005a55a9  mov      ebx, eax
005a55ab  mov      eax, dword ptr [esi + 4]
005a55ae  add      esp, 0x14
005a55b1  cmp      ebx, eax
005a55b3  mov      dword ptr [esp + 0x18], eax
005a55b7  mov      edi, ebx
005a55b9  je       0x5a55ea
005a55bb  jmp      0x5a55c0
005a55bd  lea      ecx, [ecx]
005a55c0  mov      eax, dword ptr [edi + 0xc]
005a55c3  test     eax, eax
005a55c5  je       0x5a55d0
005a55c7  push     eax
005a55c8  call     0x90cf63
005a55cd  add      esp, 4
005a55d0  mov      eax, dword ptr [edi]
005a55d2  test     eax, eax
005a55d4  je       0x5a55df
005a55d6  push     eax
005a55d7  call     0x90cf63
005a55dc  add      esp, 4
005a55df  mov      eax, dword ptr [esp + 0x18]
005a55e3  add      edi, 0x1c
005a55e6  cmp      edi, eax
005a55e8  jne      0x5a55c0
005a55ea  mov      dword ptr [esi + 4], ebx
005a55ed  jmp      0x5a55ff
005a55ef  lea      edx, [esp + 0x40]
005a55f3  push     edx
005a55f4  sub      ecx, eax
005a55f6  push     ecx
005a55f7  push     edi
005a55f8  mov      ecx, esi
005a55fa  call     0x58a170
005a55ff  mov      eax, dword ptr [esi]
005a5601  mov      ecx, dword ptr [esi + 4]
005a5604  sub      ecx, eax
005a5606  mov      eax, 0x92492493
005a560b  imul     ecx
005a560d  add      edx, ecx
005a560f  sar      edx, 4
005a5612  mov      eax, edx
005a5614  shr      eax, 0x1f
005a5617  xor      edi, edi
005a5619  add      eax, edx
005a561b  je       0x5a5650
005a561d  xor      ebx, ebx
005a561f  nop      
005a5620  mov      ecx, dword ptr [esi]
005a5622  add      ecx, ebx
005a5624  push     ecx
005a5625  push     ebp
005a5626  call     0x5ab860
005a562b  mov      edx, dword ptr [esi]
005a562d  mov      ecx, dword ptr [esi + 4]
005a5630  sub      ecx, edx
005a5632  mov      eax, 0x92492493
005a5637  imul     ecx
005a5639  add      edx, ecx
005a563b  sar      edx, 4
005a563e  mov      eax, edx
005a5640  shr      eax, 0x1f
005a5643  add      esp, 8
005a5646  inc      edi
005a5647  add      eax, edx
005a5649  add      ebx, 0x1c
005a564c  cmp      edi, eax
005a564e  jb       0x5a5620
005a5650  mov      ecx, dword ptr [esp + 0x28]
005a5654  mov      esi, dword ptr [ecx + 0xc8]
005a565a  mov      edx, dword ptr [ebp]
005a565d  lea      eax, [esp + 0x20]
005a5661  push     eax
005a5662  mov      ecx, ebp
005a5664  add      esi, 0x14
005a5667  call     dword ptr [edx + 0x24]
005a566a  mov      ecx, dword ptr [esi + 4]
005a566d  mov      edi, dword ptr [esi]
005a566f  mov      edx, dword ptr [esp + 0x20]
005a5673  mov      eax, ecx
005a5675  sub      eax, edi
005a5677  sar      eax, 2
005a567a  cmp      edx, eax
005a567c  mov      dword ptr [esp + 0x18], 0
005a5684  jae      0x5a56cb
005a5686  push     0
005a5688  lea      eax, [esp + 0x17]
005a568c  push     eax
005a568d  lea      edx, [edi + edx*4]
005a5690  push     edx
005a5691  push     ecx
005a5692  push     ecx
005a5693  call     0x586b00
005a5698  mov      ebx, eax
005a569a  mov      eax, dword ptr [esi + 4]
005a569d  add      esp, 0x14
005a56a0  cmp      ebx, eax
005a56a2  mov      dword ptr [esp + 0x18], eax
005a56a6  mov      edi, ebx
005a56a8  je       0x5a56c6
005a56aa  lea      ebx, [ebx]
005a56b0  mov      ecx, dword ptr [edi]
005a56b2  test     ecx, ecx
005a56b4  je       0x5a56bf
005a56b6  mov      edx, dword ptr [ecx]
005a56b8  call     dword ptr [edx + 0x14]
005a56bb  mov      eax, dword ptr [esp + 0x18]
005a56bf  add      edi, 4
005a56c2  cmp      edi, eax
005a56c4  jne      0x5a56b0
005a56c6  mov      dword ptr [esi + 4], ebx
005a56c9  jmp      0x5a56db
005a56cb  lea      edi, [esp + 0x18]
005a56cf  push     edi
005a56d0  sub      edx, eax
005a56d2  push     edx
005a56d3  push     ecx
005a56d4  mov      ecx, esi
005a56d6  call     0x5a46e0
005a56db  mov      eax, dword ptr [esi + 4]
005a56de  sub      eax, dword ptr [esi]
005a56e0  sar      eax, 2
005a56e3  test     eax, eax
005a56e5  mov      dword ptr [esp + 0x14], 0
005a56ed  jbe      0x5a575c
005a56ef  nop      
005a56f0  push     0x34
005a56f2  call     0x5e55e0
005a56f7  add      esp, 4
005a56fa  test     eax, eax
005a56fc  je       0x5a5709
005a56fe  mov      ecx, eax
005a5700  call     0x5812f0
005a5705  mov      ebx, eax
005a5707  jmp      0x5a570b
005a5709  xor      ebx, ebx
005a570b  mov      eax, dword ptr [esp + 0x14]
005a570f  mov      edi, dword ptr [esi]
005a5711  shl      eax, 2
005a5714  add      edi, eax
005a5716  mov      eax, dword ptr [edi]
005a5718  cmp      ebx, eax
005a571a  mov      dword ptr [esp + 0x18], eax
005a571e  je       0x5a573c
005a5720  test     ebx, ebx
005a5722  je       0x5a572b
005a5724  mov      edx, dword ptr [ebx]
005a5726  mov      ecx, ebx
005a5728  call     dword ptr [edx + 0x10]
005a572b  mov      eax, dword ptr [esp + 0x18]
005a572f  test     eax, eax
005a5731  mov      dword ptr [edi], ebx
005a5733  je       0x5a573c
005a5735  mov      ecx, eax
005a5737  mov      eax, dword ptr [ecx]
005a5739  call     dword ptr [eax + 0x14]
005a573c  mov      ecx, dword ptr [esi]
005a573e  mov      edi, dword ptr [esp + 0x14]
005a5742  mov      ecx, dword ptr [ecx + edi*4]
005a5745  mov      edx, dword ptr [ecx]
005a5747  push     ebp
005a5748  call     dword ptr [edx + 8]
005a574b  mov      eax, dword ptr [esi + 4]
005a574e  sub      eax, dword ptr [esi]
005a5750  inc      edi
005a5751  sar      eax, 2
005a5754  cmp      edi, eax
005a5756  mov      dword ptr [esp + 0x14], edi
005a575a  jb       0x5a56f0
005a575c  mov      ecx, dword ptr [esp + 0x28]
005a5760  mov      esi, dword ptr [ecx + 0xc8]
005a5766  mov      edx, dword ptr [ebp]
005a5769  lea      eax, [esp + 0x20]
005a576d  push     eax
005a576e  mov      ecx, ebp
005a5770  add      esi, 0x34
005a5773  call     dword ptr [edx + 0x24]
005a5776  mov      ecx, dword ptr [esi + 4]
005a5779  mov      edi, dword ptr [esi]
005a577b  mov      edx, dword ptr [esp + 0x20]
005a577f  mov      eax, ecx
005a5781  sub      eax, edi
005a5783  sar      eax, 2
005a5786  cmp      edx, eax
005a5788  mov      dword ptr [esp + 0x18], 0
005a5790  jae      0x5a57d1
005a5792  push     0
005a5794  lea      eax, [esp + 0x17]
005a5798  push     eax
005a5799  lea      edx, [edi + edx*4]
005a579c  push     edx
005a579d  push     ecx
005a579e  push     ecx
005a579f  call     0x586b00
005a57a4  mov      ebx, eax
005a57a6  mov      eax, dword ptr [esi + 4]
005a57a9  add      esp, 0x14
005a57ac  cmp      ebx, eax
005a57ae  mov      dword ptr [esp + 0x18], eax
005a57b2  mov      edi, ebx
005a57b4  je       0x5a57cc
005a57b6  mov      ecx, dword ptr [edi]
005a57b8  test     ecx, ecx
005a57ba  je       0x5a57c5
005a57bc  mov      edx, dword ptr [ecx]
005a57be  call     dword ptr [edx + 0x14]
005a57c1  mov      eax, dword ptr [esp + 0x18]
005a57c5  add      edi, 4
005a57c8  cmp      edi, eax
005a57ca  jne      0x5a57b6
005a57cc  mov      dword ptr [esi + 4], ebx
005a57cf  jmp      0x5a57e1
005a57d1  lea      edi, [esp + 0x18]
005a57d5  push     edi
005a57d6  sub      edx, eax
005a57d8  push     edx
005a57d9  push     ecx
005a57da  mov      ecx, esi
005a57dc  call     0x5a46e0
005a57e1  mov      eax, dword ptr [esi + 4]
005a57e4  sub      eax, dword ptr [esi]
005a57e6  sar      eax, 2
005a57e9  test     eax, eax
005a57eb  mov      dword ptr [esp + 0x14], 0
005a57f3  jbe      0x5a5861
005a57f5  push     0x1c
005a57f7  call     0x5e55e0
005a57fc  add      esp, 4
005a57ff  test     eax, eax
005a5801  je       0x5a580e
005a5803  mov      ecx, eax
005a5805  call     0x580f10
005a580a  mov      ebx, eax
005a580c  jmp      0x5a5810
005a580e  xor      ebx, ebx
005a5810  mov      eax, dword ptr [esp + 0x14]
005a5814  mov      edi, dword ptr [esi]
005a5816  shl      eax, 2
005a5819  add      edi, eax
005a581b  mov      eax, dword ptr [edi]
005a581d  cmp      ebx, eax
005a581f  mov      dword ptr [esp + 0x18], eax
005a5823  je       0x5a5841
005a5825  test     ebx, ebx
005a5827  je       0x5a5830
005a5829  mov      edx, dword ptr [ebx]
005a582b  mov      ecx, ebx
005a582d  call     dword ptr [edx + 0x10]
005a5830  mov      eax, dword ptr [esp + 0x18]
005a5834  test     eax, eax
005a5836  mov      dword ptr [edi], ebx
005a5838  je       0x5a5841
005a583a  mov      ecx, eax
005a583c  mov      eax, dword ptr [ecx]
005a583e  call     dword ptr [eax + 0x14]
005a5841  mov      ecx, dword ptr [esi]
005a5843  mov      edi, dword ptr [esp + 0x14]
005a5847  mov      ecx, dword ptr [ecx + edi*4]
005a584a  mov      edx, dword ptr [ecx]
005a584c  push     ebp
005a584d  call     dword ptr [edx + 8]
005a5850  mov      eax, dword ptr [esi + 4]
005a5853  sub      eax, dword ptr [esi]
005a5855  inc      edi
005a5856  sar      eax, 2
005a5859  cmp      edi, eax
005a585b  mov      dword ptr [esp + 0x14], edi
005a585f  jb       0x5a57f5
005a5861  mov      ecx, dword ptr [esp + 0x28]
005a5865  mov      esi, dword ptr [ecx + 0xc8]
005a586b  mov      edx, dword ptr [ebp]
005a586e  lea      eax, [esp + 0x20]
005a5872  push     eax
005a5873  mov      ecx, ebp
005a5875  add      esi, 0x54
005a5878  call     dword ptr [edx + 0x24]
005a587b  mov      ecx, dword ptr [esi + 4]
005a587e  mov      edi, dword ptr [esi]
005a5880  mov      edx, dword ptr [esp + 0x20]
005a5884  mov      eax, ecx
005a5886  sub      eax, edi
005a5888  sar      eax, 2
005a588b  cmp      edx, eax
005a588d  mov      dword ptr [esp + 0x18], 0
005a5895  jae      0x5a58db
005a5897  push     0
005a5899  lea      eax, [esp + 0x17]
005a589d  push     eax
005a589e  lea      edx, [edi + edx*4]
005a58a1  push     edx
005a58a2  push     ecx
005a58a3  push     ecx
005a58a4  call     0x586b00
005a58a9  mov      ebx, eax
005a58ab  mov      eax, dword ptr [esi + 4]
005a58ae  add      esp, 0x14
005a58b1  cmp      ebx, eax
005a58b3  mov      dword ptr [esp + 0x18], eax
005a58b7  mov      edi, ebx
005a58b9  je       0x5a58d6
005a58bb  jmp      0x5a58c0
005a58bd  lea      ecx, [ecx]
005a58c0  mov      ecx, dword ptr [edi]
005a58c2  test     ecx, ecx
005a58c4  je       0x5a58cf
005a58c6  mov      edx, dword ptr [ecx]
005a58c8  call     dword ptr [edx + 0x14]
005a58cb  mov      eax, dword ptr [esp + 0x18]
005a58cf  add      edi, 4
005a58d2  cmp      edi, eax
005a58d4  jne      0x5a58c0
005a58d6  mov      dword ptr [esi + 4], ebx
005a58d9  jmp      0x5a58eb
005a58db  lea      edi, [esp + 0x18]
005a58df  push     edi
005a58e0  sub      edx, eax
005a58e2  push     edx
005a58e3  push     ecx
005a58e4  mov      ecx, esi
005a58e6  call     0x5a46e0
005a58eb  mov      eax, dword ptr [esi + 4]
005a58ee  sub      eax, dword ptr [esi]
005a58f0  sar      eax, 2
005a58f3  test     eax, eax
005a58f5  mov      dword ptr [esp + 0x14], 0
005a58fd  jbe      0x5a596c
005a58ff  nop      
005a5900  push     0x50
005a5902  call     0x5e55e0
005a5907  add      esp, 4
005a590a  test     eax, eax
005a590c  je       0x5a5919
005a590e  mov      ecx, eax
005a5910  call     0x5bc9d0
005a5915  mov      ebx, eax
005a5917  jmp      0x5a591b
005a5919  xor      ebx, ebx
005a591b  mov      eax, dword ptr [esp + 0x14]
005a591f  mov      edi, dword ptr [esi]
005a5921  shl      eax, 2
005a5924  add      edi, eax
005a5926  mov      eax, dword ptr [edi]
005a5928  cmp      ebx, eax
005a592a  mov      dword ptr [esp + 0x18], eax
005a592e  je       0x5a594c
005a5930  test     ebx, ebx
005a5932  je       0x5a593b
005a5934  mov      edx, dword ptr [ebx]
005a5936  mov      ecx, ebx
005a5938  call     dword ptr [edx + 0x10]
005a593b  mov      eax, dword ptr [esp + 0x18]
005a593f  test     eax, eax
005a5941  mov      dword ptr [edi], ebx
005a5943  je       0x5a594c
005a5945  mov      ecx, eax
005a5947  mov      eax, dword ptr [ecx]
005a5949  call     dword ptr [eax + 0x14]
005a594c  mov      ecx, dword ptr [esi]
005a594e  mov      edi, dword ptr [esp + 0x14]
005a5952  mov      ecx, dword ptr [ecx + edi*4]
005a5955  mov      edx, dword ptr [ecx]
005a5957  push     ebp
005a5958  call     dword ptr [edx + 8]
005a595b  mov      eax, dword ptr [esi + 4]
005a595e  sub      eax, dword ptr [esi]
005a5960  inc      edi
