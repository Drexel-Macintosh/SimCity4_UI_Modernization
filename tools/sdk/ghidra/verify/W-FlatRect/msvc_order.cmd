@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat" >nul
cd /d C:\dev\SC4UIScale\tools\sdk\ghidra\verify\W-FlatRect
cl /nologo /c /O1 /GR- /FAs /Famsvc_order.asm msvc_order.cpp > msvc_order.log 2>&1
echo exit=%ERRORLEVEL%
