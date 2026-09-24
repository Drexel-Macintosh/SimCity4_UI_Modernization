@echo off
rem Builds SC4HeaderTest.dll against the fixed gzcom-dll (C:\dev\gzcom-dll-fork, branch fix-vtable-order).
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat" >nul
set FORK=C:\dev\gzcom-dll-fork\gzcom-dll
set OUT=%~dp0_build
if not exist "%OUT%" mkdir "%OUT%"
cd /d "%OUT%"
cl /nologo /LD /O2 /MT /EHsc /std:c++17 /I"%FORK%\include" "%~dp0SC4HeaderTest.cpp" "%FORK%\src\cRZCOMDllDirector.cpp" "%FORK%\src\cRZBaseString.cpp" "%FORK%\src\cRZBaseUnknown.cpp" /link /OUT:SC4HeaderTest.dll user32.lib comctl32.lib
echo EXIT=%ERRORLEVEL%
