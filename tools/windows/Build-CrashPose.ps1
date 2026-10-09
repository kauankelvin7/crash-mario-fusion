#Requires -Version 7.0
[CmdletBinding()]
param()
. "$PSScriptRoot/Common.ps1"
Use-Dotnet
# Fresh directory required. Stock launcher, pinned checkout and its mods stay untouched.
Invoke-Logged 'python' @((Join-Path $TaskRepo 'tools/prepare_crash_pose.py')) 'crash-pose-prepare.log'
$private = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M3-crash-pose'
$project = Join-Path $private 'source/CrashBandicoot.Launcher'
Invoke-Logged $TaskDotnet @('build',$project,'-c','Release','-f','net10.0-windows',
    '-p:PlatformTarget=x64','-o',(Join-Path $private 'app')) 'crash-pose-build.log'
Invoke-Logged 'python' @((Join-Path $TaskRepo 'tools/prepare_crash_pose.py'),'--seal') 'crash-pose-seal.log'
Write-Output 'Private Crash diagnostic launcher built. No game was launched; calibration is blocked.'
