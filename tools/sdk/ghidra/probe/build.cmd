@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars32.bat" >nul
cl /nologo /c /O2 /FAs /I..\..\..\..\vendor\gzcom-dll\gzcom-dll\include vtprobe.cpp
