# Requires PowerShell 7; changes affect this process and a private local cache only.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
if (-not $IsWindows -or -not [Environment]::Is64BitOperatingSystem) {
    throw 'Native Windows 10/11 x64 is required. Cloud/Linux results are separate.'
}
$TaskRepo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$TaskCache = Join-Path $env:LOCALAPPDATA 'CrashMarioFusion/M0'
$TaskLogs = Join-Path $TaskCache ('logs/' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Force $TaskLogs | Out-Null
function Invoke-Logged {
    param([string]$Command, [string[]]$Arguments, [string]$LogName)
    & $Command @Arguments 2>&1 | Tee-Object -FilePath (Join-Path $TaskLogs $LogName)
    $code = $LASTEXITCODE
    if ($code -ne 0) { throw "$Command failed ($code); see $TaskLogs/$LogName" }
}
function Use-Dotnet {
    $script:TaskDotnet = Join-Path $TaskCache 'dotnet/dotnet.exe'
    if (-not (Test-Path -LiteralPath $TaskDotnet)) { throw 'Run Setup.ps1 first.' }
    $version = & $TaskDotnet --version
    if ($LASTEXITCODE -ne 0 -or $version -ne '10.0.401') { throw 'Expected .NET SDK 10.0.401.' }
    $env:DOTNET_CLI_HOME = Join-Path $TaskCache 'dotnet-home'
    $env:DOTNET_ROOT = Join-Path $TaskCache 'dotnet'
    $env:NUGET_PACKAGES = Join-Path $TaskCache 'nuget'
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
}
function Invoke-Msys {
    param([string]$CommandText, [string]$LogName)
    $bash = Join-Path $MsysRoot 'usr/bin/bash.exe'
    if (-not (Test-Path -LiteralPath $bash)) { throw 'Install official MSYS2 first; set -MsysRoot.' }
    $env:MSYSTEM = 'MINGW64'
    $env:CHERE_INVOKING = '1'
    Invoke-Logged $bash @('-lc', "set -euo pipefail; $CommandText") $LogName
}
function Convert-MsysPath {
    param([string]$Path)
    # Paths become data, never shell commands. Reject a quote before shell interpolation.
    if ($Path.Contains("'")) { throw 'Use paths without single quotes for the MSYS2 build.' }
    $cygpath = Join-Path $MsysRoot 'usr/bin/cygpath.exe'
    $converted = & $cygpath -u $Path
    if ($LASTEXITCODE -ne 0) { throw 'cygpath failed.' }
    return $converted
}
