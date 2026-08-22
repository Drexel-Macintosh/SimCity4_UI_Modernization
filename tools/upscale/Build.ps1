# Builds Upscale2x.exe from Upscale2x.cs (x64 .NET Framework 4, System.Drawing).
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $csc /nologo /target:exe /platform:anycpu /optimize+ `
    /reference:System.Drawing.dll `
    /out:"$here\Upscale2x.exe" "$here\Upscale2x.cs"
if ($LASTEXITCODE -eq 0) { Write-Host "Built $here\Upscale2x.exe" } else { Write-Host "BUILD FAILED ($LASTEXITCODE)" }
exit $LASTEXITCODE
