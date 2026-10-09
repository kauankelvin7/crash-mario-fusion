#Requires -Version 7.0
[CmdletBinding()]
param([string]$MsysRoot = 'C:/msys64', [string]$Chdman)
. "$PSScriptRoot/Common.ps1"
Use-Dotnet
$repo = Convert-MsysPath $TaskRepo
$lib = Convert-MsysPath (Join-Path $TaskCache 'libsm64')
$cache = Convert-MsysPath $TaskCache
Invoke-Msys "cd '$repo'; python -m unittest discover -s tests -v; gcc -std=c11 -Wall -Wextra -Werror -UNDEBUG -I'$lib/src' tools/probe_libsm64.c '$lib/dist/sm64.dll' -lm -o '$cache/probe-libsm64.exe'; export PATH='$lib/dist':`$PATH; '$cache/probe-libsm64.exe'" 'synthetic-tests.log'
$launcher = Join-Path $TaskCache 'CrashBandicoot-Launcher'
Invoke-Logged $TaskDotnet @((Join-Path $launcher 'CrashBandicoot.Launcher/bin/Release/net10.0-windows/CrashBandicoot.dll'),'--help') 'launcher-cli.log'
if ($Chdman) {
    $chd = (Resolve-Path -LiteralPath $Chdman).Path
    Invoke-Logged $TaskDotnet @('run','--project',(Join-Path $launcher 'tools/CrashBandicoot.DiscCheck'),
        '-c','Release','--',$chd,(Join-Path $TaskCache 'disc-check')) 'disc-check.log'
} else { Write-Output 'NOT_TESTED: optional DiscCheck; supply your official MAME chdman.exe via -Chdman.' }
Write-Output "VERIFIED_SYNTHETIC: executed native library/configuration/CLI checks passed. Logs: $TaskLogs"
Write-Output 'Real gameplay, graphics and shared events remain NOT_TESTED by this script.'
