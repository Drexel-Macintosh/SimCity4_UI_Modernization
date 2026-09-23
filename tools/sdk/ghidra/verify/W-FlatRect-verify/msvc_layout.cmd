@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat" >nul 2>nul
cd /d C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-FlatRect-verify
cl /nologo /c /EHsc /Od /FAs /Famsvc_layout.asm /d1reportAllClassLayout msvc_layout.cpp /Fomsvc_layout.obj > msvc_layout.txt 2>&1
echo exit %ERRORLEVEL% >> msvc_layout.txt
