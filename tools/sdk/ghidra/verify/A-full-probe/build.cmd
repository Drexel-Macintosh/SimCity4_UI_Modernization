@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat" >nul
cd /d "C:\dev\SC4UIScale\tools\sdk\ghidra\verify\A-full-probe"
cl /nologo /c /O2 /FAs /I"C:\dev\SC4UIScale\vendor\gzcom-dll\gzcom-dll\include" allprobe.cpp > build.log 2>&1
echo EXIT=%ERRORLEVEL% >> build.log
