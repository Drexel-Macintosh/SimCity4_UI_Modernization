@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat" >nul
cd /d C:\dev\SC4UIScale\tools\sdk\ghidra\verify\B-second-class-exe-decode-verify
cl /nologo /c /Zs /d1reportSingleClassLayoutcIGZWin /I C:\dev\SC4UIScale\vendor\gzcom-dll\gzcom-dll\include msvc_slots.cpp > msvc_layout.txt 2>&1
echo EXIT %ERRORLEVEL%
