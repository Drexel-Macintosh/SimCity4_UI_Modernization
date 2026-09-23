@echo off
rem Regenerate out\SimCity4.gdt.json from 0xC0000054/sc4-ghidra-symbols.
rem Needs: Ghidra 12.x (GHIDRA_HOME) and a clone of the symbols repo (SC4_SYMBOLS).
rem Headless Ghidra wants a program to run a script against; any small PE will
rem do - it is imported without analysis into a throwaway project and deleted.
setlocal
if "%GHIDRA_HOME%"=="" set GHIDRA_HOME=C:\dev\tools\ghidra_12.1.4_PUBLIC
if "%SC4_SYMBOLS%"=="" set SC4_SYMBOLS=C:\dev\sc4-ghidra-symbols
set HERE=%~dp0
set PROJ=%TEMP%\sc4-gdt-export
if not exist "%PROJ%" mkdir "%PROJ%"
call "%GHIDRA_HOME%\support\analyzeHeadless.bat" "%PROJ%" tmp -import "%SystemRoot%\System32\whoami.exe" -noanalysis -deleteProject -scriptPath "%HERE%." -postScript ExportGdt.java "%SC4_SYMBOLS%\SimCity4.gdt" "%HERE%out\SimCity4.gdt.json"
