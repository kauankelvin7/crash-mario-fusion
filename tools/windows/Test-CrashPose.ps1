#Requires -Version 7.0
[CmdletBinding()]
param()
. "$PSScriptRoot/Common.ps1"
Use-Dotnet
$crashRoot = Join-Path $TaskCache 'CrashBandicoot-Launcher'
Invoke-Logged $TaskDotnet @('run','--project',(Join-Path $TaskRepo 'tests/crash_pose'),
    "-p:CrashRoot=$crashRoot",'--',$TaskRepo) 'crash-pose-checks.log'
Write-Output 'Actual upstream mod compiler, RAM and event bus; fixture inputs only. No gameplay launch.'
