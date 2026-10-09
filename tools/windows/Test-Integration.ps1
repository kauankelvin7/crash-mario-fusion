#Requires -Version 7.0
[CmdletBinding()]
param([string]$MsysRoot = 'C:/msys64')
. "$PSScriptRoot/Common.ps1"
Use-Dotnet
$repo = Convert-MsysPath $TaskRepo
$cache = Convert-MsysPath $TaskCache
Invoke-Msys "cd '$repo'; gcc -std=c11 -Wall -Wextra -Werror -Iintegration/sm64 integration/sm64/cm64_coin.c tests/integration/native_sender.c -lws2_32 -o '$cache/native-coin-sender.exe'" 'sender-build.log'
$env:PATH = (Join-Path $MsysRoot 'mingw64/bin') + ';' + $env:PATH
$crashRoot = Join-Path $TaskCache 'CrashBandicoot-Launcher'
Invoke-Logged $TaskDotnet @('run','--project',(Join-Path $TaskRepo 'tests/integration'),
    "-p:CrashRoot=$crashRoot",'--',$TaskRepo,(Join-Path $TaskCache 'native-coin-sender.exe')) 'adapter-checks.log'
Write-Output 'Checks above use actual native sender, upstream mod compiler and pad event bus, with fixture RAM. VERIFIED_SYNTHETIC only.'
