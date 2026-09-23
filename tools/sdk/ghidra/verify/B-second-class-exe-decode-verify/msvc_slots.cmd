@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat" >nul
cd /d C:\dev\SC4UIScale\tools\sdk\ghidra\verify\B-second-class-exe-decode-verify
cl /nologo /c /O2 /GR- /EHsc /FAs /Famsvc_slots.asm /Fomsvc_slots.obj /I C:\dev\SC4UIScale\vendor\gzcom-dll\gzcom-dll\include msvc_slots.cpp
echo EXIT %ERRORLEVEL%
dumpbin /nologo /disasm msvc_slots.obj > msvc_slots_disasm.txt
echo DUMPBIN %ERRORLEVEL%
